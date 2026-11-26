#!/usr/bin/env python3
"""Cold-boot an OpenBSD VDI, sign in through xenodm, and verify the Xfce desktop."""

import argparse
import json
import os
from pathlib import Path
import shlex
import shutil
import socket
import subprocess
import sys
import tempfile
import time

import pexpect
from PIL import Image


GREETER = r"""
export DISPLAY=:0
for attempt in $(jot 90); do
    for cookie in /etc/X11/xenodm/authdir/authfiles/* /var/run/xenodm/authdir/authfiles/*; do
        [ -f "$cookie" ] || continue
        if XAUTHORITY="$cookie" /usr/X11R6/bin/xwininfo -root -tree 2>/dev/null |
            grep -i '"xlogin"' ; then
            exit 0
        fi
    done
    sleep 2
done
echo 'xenodm did not present the Xlogin window' >&2
tail -20 /var/log/xenodm.log >&2
exit 1
"""

SESSION = r"""
set -eu
export DISPLAY=:0 XAUTHORITY="$HOME/.Xauthority"
for program in xfce4-session xfwm4 xfce4-panel xfdesktop; do
    pgrep -x -u "$(id -u)" "$program" >/dev/null
    echo "$program is running as $(id -un)"
done
wm=$(/usr/X11R6/bin/xprop -root _NET_SUPPORTING_WM_CHECK | awk '{print $NF}')
/usr/X11R6/bin/xprop -id "$wm" _NET_WM_NAME | grep -i xfwm4
/usr/X11R6/bin/xwininfo -root | grep -e Width: -e Height:
"""

TERMINAL = r"""
set -eu
test -t 0
test -t 1
test "$(id -un)" = desktop
test "$(uname -sr)" = "OpenBSD 8.0"
test "$(uname -m)" = amd64
{
    uname -srm
    printf 'User: %s\n' "$(id -un)"
    printf 'Terminal: %s\n' "$(tty)"
    printf 'Display: %s\n' "$DISPLAY"
    /usr/X11R6/bin/xprop -id "$WINDOWID" WM_CLASS | grep -i XTerm
} > "$1/passed.tmp"
cat "$1/passed.tmp"
mv "$1/passed.tmp" "$1/passed"
sleep 180
"""

NETWORK = r"""
set -eu
/sbin/ifconfig em0 | grep 'inet '
/sbin/route -n get default | grep 'gateway:'
ftp -V -w 15 -o /dev/null https://cdn.openbsd.org/pub/OpenBSD/8.0/amd64/SHA256
echo 'Retrieved the OpenBSD release checksum list over HTTPS.'
"""


def log(message):
    print(message, flush=True)


def wait_for(description, probe, deadline, pause=3):
    log(description)
    detail = "no response"
    while time.monotonic() < deadline:
        try:
            result = probe()
        except (subprocess.TimeoutExpired, ConnectionError, FileNotFoundError) as error:
            detail = type(error).__name__
        else:
            if result.returncode == 0:
                return result.stdout.strip()
            detail = (result.stderr or result.stdout or f"exit {result.returncode}").strip()
        time.sleep(pause)
    raise RuntimeError(f"{description} timed out. Last result: {detail[-1200:]}")


class Monitor:
    def __init__(self, connection):
        self.stream = connection.makefile("rwb", buffering=0)
        if "QMP" not in json.loads(self.stream.readline()):
            raise RuntimeError("Missing QEMU monitor greeting")
        self.command("qmp_capabilities")

    def command(self, name, **arguments):
        message = {"execute": name, "arguments": arguments}
        self.stream.write(json.dumps(message).encode() + b"\n")
        while True:
            line = self.stream.readline()
            if not line:
                raise ConnectionError("QEMU monitor disconnected")
            response = json.loads(line)
            if "error" in response:
                raise RuntimeError(f"QEMU monitor rejected {name}: {response['error']}")
            if "return" in response:
                return response["return"]

    def key(self, *codes):
        self.command("send-key", keys=[{"type": "qcode", "data": code} for code in codes],
                     **{"hold-time": 55})
        time.sleep(0.13)

    def type_text(self, value):
        # OpenBSD's installed US keyboard. Characters are sent only to the QMP socket.
        base = "1234567890-=[]\\;'`,./"
        shifted = '!@#$%^&*()_+{}|:"~<>?'
        codes = "1 2 3 4 5 6 7 8 9 0 minus equal bracket_left bracket_right backslash semicolon apostrophe grave_accent comma dot slash".split()
        normal = dict(zip(base, codes))
        upper = dict(zip(shifted, codes))
        for char in value:
            if "a" <= char <= "z":
                self.key(char)
            elif "A" <= char <= "Z":
                self.key("shift", char.lower())
            elif char == " ":
                self.key("spc")
            elif char in normal:
                self.key(normal[char])
            elif char in upper:
                self.key("shift", upper[char])
            else:
                raise ValueError("Desktop password requires printable US keyboard characters")

    def screenshot(self, ppm, destination):
        self.command("screendump", filename=str(ppm))
        with Image.open(ppm) as screenshot:
            screenshot.save(destination, format="PNG")


class Guest:
    def __init__(self, temporary, port, desktop_password, root_password):
        self.root_password = root_password
        ask = temporary / "askpass"
        ask.write_text('#!/bin/sh\nprintf "%s\\n" "$OBSD_VERIFY_PASSWORD"\n')
        ask.chmod(0o700)
        self.environment = os.environ.copy()
        for variable in ("ROOT_PASSWORD", "DESKTOP_PASSWORD", "SSH_AUTH_SOCK"):
            self.environment.pop(variable, None)
        self.environment.update(SSH_ASKPASS=str(ask), SSH_ASKPASS_REQUIRE="force",
                                DISPLAY="verify", OBSD_VERIFY_PASSWORD=desktop_password)
        self.ssh = [
            "ssh", "-p", str(port), "-o", "ConnectTimeout=6", "-o", "LogLevel=ERROR",
            "-o", "StrictHostKeyChecking=accept-new", "-o", "PubkeyAuthentication=no",
            "-o", "NumberOfPasswordPrompts=1", "-o", f"UserKnownHostsFile={temporary}/hosts",
            "-o", "GlobalKnownHostsFile=/dev/null",
        ]

    def run(self, command, timeout=25):
        return subprocess.run(self.ssh + ["desktop@127.0.0.1", command],
                              stdin=subprocess.DEVNULL, capture_output=True, text=True,
                              timeout=timeout, env=self.environment)

    def root(self, command, timeout):
        # Authenticate to su on the guest PTY after its password prompt. Root SSH stays disabled.
        remote = shlex.join(["env", "LC_ALL=C", "su", "root", "-c", command])
        args = self.ssh[1:] + ["-tt", "desktop@127.0.0.1", remote]
        with pexpect.spawn("ssh", args, encoding="utf-8", echo=False, timeout=timeout,
                           env=self.environment) as session:
            if session.expect([r"(?i)password:\s*$", pexpect.EOF]) == 0:
                session.sendline(self.root_password)
                session.expect(pexpect.EOF)
            output = session.before.replace(self.root_password, "[redacted]").strip()
            session.close()
            return subprocess.CompletedProcess("su", session.exitstatus, output, "")

def available_port():
    with socket.socket() as port:
        port.bind(("127.0.0.1", 0))
        return port.getsockname()[1]


def connect_monitor(path, qemu):
    expiry = time.monotonic() + 30
    while time.monotonic() < expiry:
        if qemu.poll() is not None:
            raise RuntimeError("QEMU exited during startup. See qemu.log.")
        connection = socket.socket(socket.AF_UNIX)
        try:
            connection.settimeout(20)
            connection.connect(str(path))
            return connection
        except (FileNotFoundError, ConnectionRefusedError):
            connection.close()
            time.sleep(0.2)
    raise RuntimeError("QEMU monitor did not become available")


def checked(result, description):
    if result.returncode != 0:
        raise RuntimeError(f"{description} failed ({result.returncode}): "
                           f"{(result.stderr or result.stdout or '').strip()[-1500:]}")
    return result.stdout.strip()


def verify(guest, monitor, temporary, evidence, password, deadline):
    def phase(seconds):
        return min(time.monotonic() + seconds, deadline)

    report = []
    start = wait_for("Booting the installed disk and checking SSH", lambda:
                     guest.run("sysctl -n kern.boottime"), phase(600))
    log("Checking for the xenodm login window")
    report.append(checked(guest.root(GREETER, timeout=200), "Checking xenodm"))
    checked(guest.run('! pgrep -x -u "$(id -u)" xfce4-session >/dev/null'),
            "Checking for a fresh login")
    monitor.type_text("desktop")
    monitor.key("ret")
    time.sleep(0.7)
    monitor.type_text(password)
    monitor.key("ret")

    report.append(wait_for("Checking Xfce processes and its X11 window manager",
                           lambda: guest.run(SESSION), phase(240)))
    work = checked(guest.run("mktemp -d /tmp/desktop-proof.XXXXXXXX"), "Creating guest work directory")
    title = "OpenBSD desktop verification"
    command = shlex.join(["/usr/X11R6/bin/xterm", "-T", title, "-geometry", "65x8+48+85",
                          "-e", "/bin/sh", "-c", TERMINAL, "verify", work])
    checked(guest.run(f'DISPLAY=:0 XAUTHORITY="$HOME/.Xauthority" '
                      f'nohup {command} </dev/null >/dev/null 2>&1 &'), "Opening the X terminal")
    proof = (f'DISPLAY=:0 XAUTHORITY="$HOME/.Xauthority" /usr/X11R6/bin/xwininfo -root -tree '
             f'| grep -F {shlex.quote(title)} && cat {shlex.quote(work)}/passed')
    report.append(wait_for("Checking the visible terminal and its interactive shell",
                           lambda: guest.run(proof), phase(90)))
    monitor.screenshot(temporary / "desktop.ppm", evidence / "desktop.png")
    report.append(wait_for("Checking guest networking and outbound HTTPS",
                           lambda: guest.run(NETWORK, timeout=35), phase(120)))

    log("Rebooting OpenBSD and checking for a new boot and login window")
    # The SSH transport can disappear while shutdown is in progress. Confirm using the guest's clock.
    reboot = guest.root("/sbin/shutdown -r now", timeout=60)
    if reboot.returncode not in (0, 255):
        checked(reboot, "Requesting a guest reboot")
    new_boot = (f'boot=$(sysctl -n kern.boottime) && [ -n "$boot" ] '
                f'&& [ "$boot" != {shlex.quote(start)} ] && echo "$boot"')
    booted = wait_for("Waiting for the rebooted system", lambda: guest.run(new_boot), phase(600))
    report.append(f"First boot: {start}\nSecond boot: {booted}")
    report.append(checked(guest.root(GREETER, timeout=200), "Checking xenodm after reboot"))
    (evidence / "verification.txt").write_text("\n".join(report) + "\n")
    log("Verified graphical login, Xfce, an interactive X terminal, networking, and guest reboot.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--disk", required=True, type=Path)
    parser.add_argument("--evidence", required=True, type=Path)
    parser.add_argument("--timeout", type=int, default=1800, help="total time budget in seconds")
    args = parser.parse_args()
    disk = args.disk.resolve(strict=True)
    evidence = args.evidence.resolve()
    evidence.mkdir(parents=True, exist_ok=True)
    for dep in ("qemu-system-x86_64", "qemu-img", "ssh"):
        if not shutil.which(dep):
            raise RuntimeError(f"Missing program: {dep}")
    password = os.environ.get("DESKTOP_PASSWORD")
    root_password = os.environ.get("ROOT_PASSWORD")
    if not password or not root_password:
        raise ValueError("Set DESKTOP_PASSWORD and ROOT_PASSWORD")
    if not all(" " <= char <= "~" for char in password):
        raise ValueError("Desktop password requires printable US keyboard characters")
    deadline = time.monotonic() + args.timeout
    with tempfile.TemporaryDirectory(prefix="obsd-verify-") as directory:
        temporary = Path(directory)
        overlay = temporary / "verification.qcow2"
        subprocess.run(["qemu-img", "create", "-q", "-f", "qcow2", "-F", "vdi",
                        "-b", str(disk), str(overlay)], check=True)
        port = available_port()
        guest = Guest(temporary, port, password, root_password)
        monitor_path = temporary / "qmp"
        command = [
            "qemu-system-x86_64", "-machine", "pc,accel=kvm:tcg", "-cpu", "max",
            "-m", "2048", "-smp", "2", "-nodefaults", "-display", "none", "-vga", "std",
            "-device", "ich9-ahci,id=sata", "-drive", f"file={overlay},if=none,id=os,format=qcow2",
            "-device", "ide-hd,drive=os,bus=sata.0,bootindex=1",
            "-nic", f"user,model=e1000,hostfwd=tcp:127.0.0.1:{port}-:22",
            "-qmp", f"unix:{monitor_path},server=on,wait=off",
        ]
        with (evidence / "qemu.log").open("w") as diagnostics:
            qemu = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=diagnostics,
                                    stderr=subprocess.STDOUT)
            try:
                with connect_monitor(monitor_path, qemu) as connection:
                    monitor = Monitor(connection)
                    try:
                        verify(guest, monitor, temporary, evidence, password, deadline)
                    finally:
                        monitor.stream.close()
            finally:
                if qemu.poll() is None:
                    qemu.terminate()
                    try:
                        qemu.wait(timeout=12)
                    except subprocess.TimeoutExpired:
                        qemu.kill()
                        qemu.wait()


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, ValueError, OSError, subprocess.SubprocessError,
            pexpect.ExceptionPexpect) as error:
        # Timeout tracebacks can include terminal buffers. Keep credentials out of diagnostics.
        message = str(error) if not isinstance(error, pexpect.ExceptionPexpect) else type(error).__name__
        for secret in ("ROOT_PASSWORD", "DESKTOP_PASSWORD"):
            if value := os.environ.get(secret):
                message = message.replace(value, "[redacted]")
        sys.exit(f"Desktop verification failed: {message}")
