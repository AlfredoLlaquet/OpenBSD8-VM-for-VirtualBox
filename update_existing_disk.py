#!/usr/bin/env python3
"""Change the published login passwords in an existing OpenBSD VDI without reinstalling it."""

import argparse
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
import time

import bcrypt
import pexpect

from verify_desktop import Guest, Monitor, available_port, checked, connect_monitor, log, redact, wait_for


DEFAULT_DESKTOP_PASSWORD = "OpenSesame"
DEFAULT_ROOT_PASSWORD = "CheckOut_TheCrumbs.org"

INVENTORY = r"""
set -eu
PATH=/bin:/usr/bin:/sbin:/usr/sbin:/usr/local/bin:/usr/local/sbin
export PATH
printf 'OpenBSD 8 with Xfce for VirtualBox — installed image inventory\n\n'
printf 'Operating system and kernel\n'
uname -a
printf '\nArchitecture\n'
machine -a
printf '\nHostname\n'
hostname
printf '\nTimezone file\n'
ls -l /etc/localtime
printf '\nInstalled package versions\n'
pkg_info -q | sort
printf '\nInstalled system patches (an empty list means none)\n'
syspatch -l || test "$?" -eq 2
printf '\nDisk partitions (GiB)\n'
disklabel -p g sd0
printf '\nFilesystems and current space usage\n'
df -h
printf '\nConfigured local services\n'
cat /etc/rc.conf.local
printf '\nDesktop account and groups\n'
id desktop
printf '\nSSH server configuration validation\n'
if /usr/sbin/sshd -t; then
    printf 'Configuration and host keys passed sshd -t.\n'
else
    status=$?
    printf 'sshd -t failed with status %s.\n' "$status" >&2
    exit "$status"
fi
printf '\nEffective SSH server configuration\n'
if /usr/sbin/sshd -G; then
    :
else
    status=$?
    printf 'sshd -G failed with status %s.\n' "$status" >&2
    exit "$status"
fi
printf '\nBoot console\n'
cat /etc/boot.conf
printf '\nNetwork configuration\n'
cat /etc/hostname.em0
printf '\nPackage mirror\n'
cat /etc/installurl
"""

READY_TO_HALT = r"""
set -eu
PATH=/bin:/usr/bin:/sbin:/usr/sbin
export PATH
kernel=$(sysctl -n kern.osversion)
relink_log="/usr/share/relink/kernel/${kernel%%#*}/relink.log"
attempt=0
while pgrep -U 0 -qxf '/bin/ksh .*reorder_kernel$'; do
    [ "$attempt" -lt 180 ] || { echo 'Kernel relinking did not finish within 15 minutes.' >&2; exit 1; }
    attempt=$((attempt + 1))
    sleep 5
done
test -f "$relink_log"
grep -Fq 'Kernel has been relinked and is active on next reboot.' "$relink_log"
sha256 -C /var/db/kernel.SHA256 /bsd
echo 'Native kernel relinking completed and the next boot kernel checksum is correct.'
"""

HALT = r"""
set -eu
# The next owner receives fresh SSH host keys, as in the original image.
rm -f /etc/ssh/ssh_host_*_key /etc/ssh/ssh_host_*_key.pub /var/db/dhcpleased/em0
sync
echo 'Guest is prepared for a clean power-off.'
/sbin/shutdown -p now
"""


def validate_password(value, label):
    if not value.isascii() or not value.isprintable() or not 1 <= len(value) <= 72:
        raise ValueError(f"{label} must contain 1–72 printable ASCII characters")
    return value


def original_credentials(path):
    """Read the legacy release note, or use explicitly supplied/current public defaults."""
    if path is not None:
        text = path.read_text(encoding="utf-8")
        desktop = re.findall(r"^Username: desktop\r?\nPassword: ([^\r\n]+)\r?$", text, re.MULTILINE)
        root = re.findall(r"^For system administration, use su - with this root password: ([^\r\n]+)\r?$",
                          text, re.MULTILINE)
        if len(desktop) != 1 or len(root) != 1:
            raise ValueError("The legacy FIRST-LOGIN.txt must identify exactly one desktop and root password")
        desktop, root = desktop[0], root[0]
    else:
        desktop = os.environ.get("OLD_DESKTOP_PASSWORD")
        root = os.environ.get("OLD_ROOT_PASSWORD")
        if bool(desktop) != bool(root):
            raise ValueError("Set both OLD_DESKTOP_PASSWORD and OLD_ROOT_PASSWORD, or neither")
        if desktop is None and root is None:
            desktop, root = DEFAULT_DESKTOP_PASSWORD, DEFAULT_ROOT_PASSWORD
    return (validate_password(desktop or "", "Old desktop password"),
            validate_password(root or "", "Old root password"))


def password_update(desktop_password, root_password):
    commands = ["set -eu", 'test "$(uname -sr)" = "OpenBSD 8.0"',
                'test "$(machine -a)" = amd64', 'test "$(id -u)" = 0']
    for user, password in (("desktop", desktop_password), ("root", root_password)):
        digest = bcrypt.hashpw(password.encode("ascii"), bcrypt.gensalt(rounds=10)).decode("ascii")
        commands.append(shlex.join(["/usr/sbin/usermod", "-p", digest, user]))
    commands += ["sync", "echo 'Both account password databases were updated.'"]
    return "\n".join(commands)


def update(args):
    source = args.disk.resolve(strict=True)
    output = args.output.resolve()
    if output.exists():
        raise FileExistsError("The output already exists; the original disk is never overwritten")
    if source == output:
        raise ValueError("Source and output must be different files")
    evidence = args.evidence.resolve()
    evidence.mkdir(parents=True, exist_ok=True)
    output.parent.mkdir(parents=True, exist_ok=True)
    inventory = args.inventory.resolve() if args.inventory else evidence / "IMAGE-INFO.txt"
    if inventory == source or inventory == output or inventory.exists():
        raise ValueError("The inventory destination must be a new, separate file")
    for dependency in ("qemu-img", "qemu-system-x86_64", "ssh"):
        if not shutil.which(dependency):
            raise RuntimeError(f"Missing program: {dependency}")
    info = json.loads(subprocess.check_output(["qemu-img", "info", "--output=json", str(source)], text=True))
    if info.get("format") != "vdi" or info.get("backing-filename"):
        raise ValueError("The source must be a standalone VDI")
    old_desktop, old_root = original_credentials(args.credentials)
    desktop_password = validate_password(os.environ.get("DESKTOP_PASSWORD", DEFAULT_DESKTOP_PASSWORD),
                                         "New desktop password")
    root_password = validate_password(os.environ.get("ROOT_PASSWORD", DEFAULT_ROOT_PASSWORD),
                                      "New root password")
    # Redact old private-release credentials even if an authentication diagnostic includes them.
    os.environ.update(OLD_DESKTOP_PASSWORD=old_desktop, OLD_ROOT_PASSWORD=old_root,
                      DESKTOP_PASSWORD=desktop_password, ROOT_PASSWORD=root_password)
    if os.environ.get("GITHUB_ACTIONS") == "true":
        for password in (old_desktop, old_root):
            print("::add-mask::" + password.replace("%", "%25"), flush=True)
    report = []
    with tempfile.TemporaryDirectory(dir=output.parent, prefix=".obsd-password-update-") as directory:
        temporary = Path(directory)
        overlay = temporary / "update.qcow2"
        subprocess.run(["qemu-img", "create", "-q", "-f", "qcow2", "-F", "vdi", "-b",
                        str(source), str(overlay)], check=True)
        port = available_port()
        guest = Guest(temporary, port, old_desktop, old_root)
        monitor_path = temporary / "qmp"
        disk_argument = str(overlay).replace(",", ",,")
        command = [
            "qemu-system-x86_64", "-machine", "pc,accel=kvm:tcg", "-cpu", "max",
            "-m", "3072", "-smp", "2", "-nodefaults", "-display", "none", "-vga", "std",
            "-rtc", "base=utc", "-device", "ich9-ahci,id=sata",
            "-drive", f"file={disk_argument},if=none,id=os,format=qcow2",
            "-device", "ide-hd,drive=os,bus=sata.0,bootindex=1",
            "-nic", f"user,model=e1000,hostfwd=tcp:127.0.0.1:{port}-:22",
            "-qmp", f"unix:{monitor_path},server=on,wait=off",
        ]
        deadline = time.monotonic() + args.timeout
        with (evidence / "update-qemu.log").open("w") as diagnostics:
            qemu = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=diagnostics,
                                    stderr=subprocess.STDOUT)

            def expire(_signum, _frame):
                raise TimeoutError(f"Image update exceeded its {args.timeout}-second budget")

            try:
                signal.signal(signal.SIGALRM, expire)
                signal.alarm(args.timeout)
                with connect_monitor(monitor_path, qemu) as connection:
                    monitor = Monitor(connection)
                    try:
                        wait_for("Booting the existing release with its original credentials",
                                 lambda: guest.run("id -un"), min(deadline, time.monotonic() + 600))
                        log("Updating the two login passwords without reinstalling OpenBSD or packages")
                        report.append(checked(guest.root(password_update(desktop_password, root_password), 90),
                                              "Updating account passwords"))
                        guest = Guest(temporary, port, desktop_password, root_password)
                        identity = wait_for("Authenticating the new desktop password",
                                            lambda: guest.run("id -un"),
                                            min(deadline, time.monotonic() + 90))
                        if identity != "desktop":
                            raise RuntimeError("The new desktop password did not authenticate as desktop")
                        identity = checked(guest.root("id -u", 45), "Authenticating the new root password")
                        if identity != "0":
                            raise RuntimeError("The new root password did not authenticate as root")
                        report.append("The new desktop and root passwords both authenticated successfully.")
                        inventory_text = checked(guest.root(INVENTORY, 90), "Reading the installed image inventory")
                        report.append(checked(guest.root(READY_TO_HALT, 1000), "Waiting for native kernel relinking"))
                        halt = guest.root(HALT, 90)
                        if halt.returncode not in (0, 255, None):
                            checked(halt, "Requesting a clean power-off")
                        qemu.wait(timeout=180)
                        if qemu.returncode != 0:
                            raise RuntimeError(f"QEMU did not power off cleanly (status {qemu.returncode})")
                        report.append("The updated guest powered off cleanly after clone identity cleanup.")
                    finally:
                        monitor.stream.close()
            finally:
                signal.alarm(0)
                if qemu.poll() is None:
                    qemu.terminate()
                    try:
                        qemu.wait(timeout=12)
                    except subprocess.TimeoutExpired:
                        qemu.kill()
                        qemu.wait()
        subprocess.run(["qemu-img", "check", "-q", "-f", "qcow2", str(overlay)], check=True)
        exported = temporary / "updated.vdi"
        log("Exporting the updated standalone VDI and comparing every guest-visible sector")
        subprocess.run(["qemu-img", "convert", "-f", "qcow2", "-O", "vdi", str(overlay), str(exported)], check=True)
        subprocess.run(["qemu-img", "compare", "-f", "qcow2", "-F", "vdi", str(overlay), str(exported)], check=True)
        inventory.parent.mkdir(parents=True, exist_ok=True)
        inventory.write_text(inventory_text + "\n", encoding="utf-8")
        (evidence / "image-update.txt").write_text("\n".join(report) + "\n", encoding="utf-8")
        os.link(exported, output)
    log(f"Updated VDI ready for an independent graphical verification: {output}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--disk", type=Path, required=True, help="Existing, checksum-verified VDI")
    parser.add_argument("--credentials", type=Path, help="Legacy FIRST-LOGIN.txt; omitted for public defaults or OLD_* environment variables")
    parser.add_argument("--output", type=Path, required=True, help="New standalone VDI; must not exist")
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--inventory", type=Path, help="IMAGE-INFO.txt destination; defaults to evidence directory")
    parser.add_argument("--timeout", type=int, default=2100, help="VM update budget in seconds")
    args = parser.parse_args()
    if args.timeout < 1:
        parser.error("--timeout must be positive")
    update(args)


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, ValueError, OSError, subprocess.SubprocessError, pexpect.ExceptionPexpect) as error:
        message = str(error) if not isinstance(error, pexpect.ExceptionPexpect) else type(error).__name__
        sys.exit(f"Existing-image update failed: {redact(message)}")
