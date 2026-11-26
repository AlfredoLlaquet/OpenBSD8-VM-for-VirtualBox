#!/usr/bin/env python3
"""Install OpenBSD 8.0/amd64 and Xfce on a new QEMU qcow2 disk."""

import argparse
import contextlib
import http.server
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time

import bcrypt
import pexpect


ISO = "install80.iso"
RELEASE_PATH = "8.0/amd64"
# https://www.openbsd.org/80.html and the project's separately distributed key.
BASE_KEY = "RWSMSt0erHTctUxq2JDAgQRo64ztikp8JvQeiSPte3NZ0Geou0TkTEiE"
MIRRORS = ("https://cdn.openbsd.org/pub/OpenBSD", "https://ftp.openbsd.org/pub/OpenBSD")
PROMPT = r"(?m)^[^\r\n]{0,45}# ?$"


def log(message):
    print(message, flush=True)


def official_media(cache):
    cache.mkdir(parents=True, exist_ok=True)
    signify = shutil.which("signify-openbsd") or shutil.which("signify")
    if not signify:
        raise RuntimeError("OpenBSD signify is required (Ubuntu package signify-openbsd).")
    key = cache / "openbsd-80-base.pub"
    key.write_text(f"untrusted comment: OpenBSD 8.0 base public key\n{BASE_KEY}\n")
    verify = [signify, "-C", "-p", str(key), "-x", "SHA256.sig", ISO]
    if (cache / ISO).is_file() and (cache / "SHA256.sig").is_file():
        if subprocess.run(verify, cwd=cache).returncode == 0:
            return cache / ISO
    with tempfile.TemporaryDirectory(dir=cache) as tmp:
        for mirror in MIRRORS:
            try:
                for name in ("SHA256.sig", ISO):
                    url = f"{mirror}/{RELEASE_PATH}/{name}"
                    log(f"Downloading {url}")
                    subprocess.run(
                        ["curl", "--fail", "--silent", "--show-error", "--location",
                         "--proto", "=https", "--proto-redir", "=https",
                         "--retry", "2", "--retry-all-errors", "--connect-timeout", "20",
                         "--max-time", "900", "--output", name, url],
                        cwd=tmp, check=True, timeout=2800,
                    )
                subprocess.run(verify, cwd=tmp, check=True)
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
                log(f"Release download or verification failed at {mirror}: {error}")
                continue
            for name in ("SHA256.sig", ISO):
                (Path(tmp) / name).replace(cache / name)
            return cache / ISO
    raise RuntimeError("Could not obtain and authenticate the official OpenBSD 8.0 amd64 ISO.")


def passwd_hash(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=10)).decode()


def installer_answers(base_url, root_password, desktop_password):
    # The install CD is authenticated as a whole before QEMU can boot it.
    # OpenBSD omits an individual SHA256.sig from its full install ISO.
    return f"""System hostname = obsd-xfce
Network interface to configure = em0
IPv4 address for em0 = autoconf
IPv6 address for em0 = none
Network interface to configure = done
Password for root account = {passwd_hash(root_password)}
Start sshd(8) by default = yes
Do you expect to run the X Window System = yes
Do you want the X Window System to be started by xenodm(1) = yes
Change the default console to com0 = yes
Which speed should com0 use = 115200
Setup a user = desktop
Full name for user desktop = Desktop
Password for user desktop = {passwd_hash(desktop_password)}
Allow root ssh login = no
What timezone are you in = UTC
Which disk is the root disk = sd0
Encrypt the root disk = no
Use (W)hole disk MBR = whole
URL to autopartitioning template for disklabel = {base_url}/layout
Location of sets = cd0
Set name(s) = all
Continue without verification = yes
Location of sets = done
Exit to (S)hell, (H)alt or (R)eboot = reboot
""".encode()


@contextlib.contextmanager
def build_server(root_password, desktop_password):
    # Guest access to a loopback-only host listener through QEMU user networking.
    prefix = "/" + secrets.token_hex(16)
    files = {}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            body = files.get(self.path)
            if body is None:
                return self.send_error(404)
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, fmt, *args):
            pass

    with http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler) as server:
        base_url = f"http://10.0.2.2:{server.server_port}{prefix}"
        files[prefix + "/install.conf"] = installer_answers(base_url, root_password, desktop_password)
        files[prefix + "/layout"] = (
            b"/ 1G-2G 5%\nswap 512M\n/tmp 256M-2G 5%\n/var 768M-4G 10%\n"
            b"/usr 3G-10G 20%\n/usr/local 4G-* 45%\n/home 1G-* 15%\n"
        )
        for stage in ("packages", "provision"):
            files[f"{prefix}/{stage}.sh"] = (Path(__file__).parent / "guest" / f"{stage}.sh").read_bytes()
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            yield base_url
        finally:
            server.shutdown()
            worker.join()


class Transcript:
    """Persist serial output; mask reusable credentials even across read boundaries."""

    def __init__(self, file, passwords):
        self.file = file
        self.passwords = passwords
        self.unfinished = ""

    def write(self, value):
        lines = (self.unfinished + value).replace("\r", "\n").split("\n")
        self.unfinished = lines.pop()
        for line in lines:
            if not line.strip():
                continue
            for secret in self.passwords:
                line = line.replace(secret, "[redacted]")
            line = re.sub(r"\$2[abxy]\$\d\d\$[./A-Za-z0-9]{53}", "[password hash]", line)
            self.file.write(line + "\n")
            # Continuous progress bars can otherwise flood the CI log.
            if not re.search(r"\d%\s*\|", line) or "100%" in line:
                log(line)

    def flush(self):
        self.file.flush()


@contextlib.contextmanager
def machine(disk, options, transcript, iso=None, monitor=None):
    machine_type = "pc,accel=" + ("kvm:tcg" if options.accel == "auto" else options.accel)
    args = [
        "-machine", machine_type, "-cpu", "max", "-smp", "2", "-m", str(options.memory),
        "-vga", "std", "-display", "none", "-serial", "stdio", "-monitor", "none",
        "-no-reboot", "-rtc", "base=utc",
        "-netdev", "user,id=nat", "-device", "e1000,netdev=nat",
        "-device", "ich9-ahci,id=sata",
        "-drive", f"if=none,id=system,file={str(disk).replace(',', ',,')},format=qcow2",
        "-device", f"ide-hd,bus=sata.0,drive=system,bootindex={2 if iso else 1}",
    ]
    if iso:
        args += [
            "-drive", f"if=none,id=cd,file={str(iso).replace(',', ',,')},media=cdrom,format=raw,readonly=on",
            "-device", "ide-cd,bus=ide.1,drive=cd,bootindex=1", "-S",
            "-qmp", f"unix:{monitor},server=on,wait=off",
        ]
    child = pexpect.spawn("qemu-system-x86_64", args, encoding="utf-8", codec_errors="replace",
                          echo=False, timeout=options.boot_timeout, env={
                              key: val for key, val in os.environ.items()
                              if key not in ("ROOT_PASSWORD", "DESKTOP_PASSWORD")
                          })
    child.logfile_read = transcript
    try:
        yield child
    finally:
        if child.isalive():
            child.terminate(force=True)
        child.close()
        transcript.write("\n")
        transcript.flush()


def expect(child, pattern, timeout, description, failure_patterns=()):
    result = child.expect([pattern, pexpect.EOF, pexpect.TIMEOUT, r"(?im)^panic:", *failure_patterns],
                          timeout=timeout)
    if result:
        if result == 1:
            cause = "QEMU exited"
        elif result == 2:
            cause = "time limit reached"
        else:
            cause = child.match.group(0).strip()
        raise RuntimeError(f"{description}: {cause}. See the serial transcript.")
    return child.match


def wait_clean_exit(child, timeout):
    if child.expect([pexpect.EOF, pexpect.TIMEOUT], timeout=timeout):
        raise RuntimeError("The guest did not finish rebooting or powering off.")
    child.close()
    if child.exitstatus != 0:
        raise RuntimeError(f"QEMU exited with status {child.exitstatus}, signal {child.signalstatus}.")


def select_serial_console(child, monitor_path, vga_dump, timeout):
    # SeaBIOS starts the unmodified CD boot loader on the VGA text screen.
    # Watch the real prompt, then type its documented console-switch command.
    deadline = time.monotonic() + timeout
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
        sock.settimeout(15)
        while True:
            try:
                sock.connect(str(monitor_path))
                break
            except (FileNotFoundError, ConnectionRefusedError):
                if not child.isalive():
                    expect(child, r"(?!)", 1, "Starting QEMU")
                if time.monotonic() >= deadline:
                    raise RuntimeError("QEMU did not open the monitor socket.")
                time.sleep(0.1)
        with sock.makefile("rwb") as stream:
            if "QMP" not in json.loads(stream.readline()):
                raise RuntimeError("QEMU monitor greeting missing.")

            def command(name, **kwargs):
                stream.write(json.dumps({"execute": name, "arguments": kwargs}).encode() + b"\n")
                stream.flush()
                while True:
                    reply = json.loads(stream.readline())
                    if "error" in reply:
                        raise RuntimeError(f"{name}: {reply['error']}")
                    if "return" in reply:
                        return reply["return"]

            command("qmp_capabilities")
            command("cont")
            screen = b""
            while time.monotonic() < deadline:
                command("pmemsave", val=0xB8000, size=80 * 25 * 2, filename=str(vga_dump))
                screen = vga_dump.read_bytes()[::2]
                if b"boot>" in screen:
                    for key in "s e t spc t t y spc c o m 0 ret".split():
                        command("send-key", keys=[{"type": "qcode", "data": key}], **{"hold-time": 25})
                        time.sleep(0.07)
                    return
                time.sleep(0.12)
            raise RuntimeError(f"OpenBSD CD boot prompt missing from VGA console: {screen!r}")


def install_system(disk, media, base_url, options, transcript):
    log("Booting the verified installer with a BIOS, SATA disk, and Intel network adapter")
    with tempfile.TemporaryDirectory(prefix="obsd-console-") as directory:
        monitor = Path(directory) / "qmp.sock"
        with machine(disk, options, transcript, iso=media, monitor=monitor) as child:
            select_serial_console(child, monitor, Path(directory) / "vga.bin", options.boot_timeout)
            expect(child, r"boot>", options.boot_timeout, "Selecting serial console")
            child.send("boot\r")
            expect(child, r"\(A\)utoinstall or \(S\)hell\?", options.boot_timeout, "Starting installer")
            child.send("a\r")
            expect(child, r"Response file location\?", options.boot_timeout, "Locating install answers")
            child.send(base_url + "/install.conf\r")
            expect(child, r"Your OpenBSD install has been successfully completed",
                   options.install_timeout, "Installing OpenBSD and X sets",
                   (r"(?i)question has no answer", r"(?i)autopartitioning failed",
                    r"(?i)autoinstall failed", r"\(A\)utoinstall or \(S\)hell\?"))
            # -no-reboot makes the installer's reboot a clean QEMU exit.
            wait_clean_exit(child, options.boot_timeout)


def run_guest_stages(disk, base_url, root_password, options, transcript, stages):
    log(f"Booting the installed disk with the CD removed for {', '.join(stages)}")
    with machine(disk, options, transcript) as child:
        expect(child, r"(?im)^.*login:\s*$", options.boot_timeout, "Booting the installed OS")
        child.send("root\r")
        expect(child, r"(?i)password:", 30, "Opening the local root session")
        child.send(root_password + "\r")
        expect(child, PROMPT, 90, "Authenticating on the serial console",
               (r"(?i)login incorrect",))
        for stage in stages:
            path = f"/tmp/obsd-{stage}.sh"
            tag = stage.upper()
            # Splitting the marker in printf keeps the echoed command distinct
            # from its result. A serial/PTY pair can emit CRLF or CRCRLF.
            child.send(f"ftp -V -o {path} '{base_url}/{stage}.sh' && sh {path}; "
                       f"rc=$?; rm -f {path}; printf '\\nOBSD_%s_RESULT=%d\\n' {tag} \"$rc\"\r")
            pattern = rf"(?:^|[\r\n])OBSD_{tag}_RESULT=([0-9]+)(?=[\r\n])"
            status = expect(child, pattern, options.package_timeout, f"Running guest stage {stage}")
            if status.group(1) != "0":
                raise RuntimeError(f"Guest stage {stage} exited with status {status.group(1)}.")
            log(f"Guest stage {stage} completed.")
        child.send("halt -p\r")
        wait_clean_exit(child, options.boot_timeout)


def check_disk(path):
    subprocess.run(["qemu-img", "check", "-q", "-f", "qcow2", str(path)], check=True)


def install_new_disk(path, url, options, transcript):
    media = official_media(options.work_dir.resolve() / "media")
    subprocess.run(["qemu-img", "create", "-f", "qcow2", str(path), options.disk_size], check=True)
    install_system(path, media, url, options, transcript)


def package_checkpoint(checkpoint, url, password, options, transcript):
    if checkpoint.exists():
        info = subprocess.check_output(["qemu-img", "info", "--output=json", str(checkpoint)])
        metadata = json.loads(info)
        if metadata.get("format") != "qcow2" or metadata.get("backing-filename"):
            raise ValueError(f"Checkpoint must be a standalone qcow2 file: {checkpoint}")
        check_disk(checkpoint)
        log(f"Using powered-off package checkpoint: {checkpoint}")
        return
    checkpoint.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=checkpoint.parent, prefix=".obsd-packages-") as tmp:
        source = Path(tmp) / "packages.qcow2"
        install_new_disk(source, url, options, transcript)
        run_guest_stages(source, url, password, options, transcript, ("packages",))
        check_disk(source)
        # Same filesystem, atomic, and cannot overwrite another build's result.
        os.link(source, checkpoint)
    log(f"Saved clean powered-off package checkpoint: {checkpoint}")


def arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("build/openbsd-xfce.qcow2"))
    parser.add_argument("--work-dir", type=Path, default=Path("build/guest"),
                        help="Directory for the verified ISO cache and serial log.")
    parser.add_argument("--checkpoint", type=Path,
                        help="Create or reuse a standalone qcow2 after packages are installed. "
                             "Resume with the same root and desktop passwords.")
    parser.add_argument("--disk-size", default="16G", help="Guest disk size, at least 12G.")
    parser.add_argument("--memory", type=int, default=3072, help="Guest RAM in MiB.")
    parser.add_argument("--accel", choices=["auto", "kvm", "tcg"], default="auto")
    parser.add_argument("--boot-timeout", type=int, default=600, help="Boot or shutdown time in seconds.")
    parser.add_argument("--install-timeout", type=int, default=5400, help="Base install timeout in seconds.")
    parser.add_argument("--package-timeout", type=int, default=7200, help="Xfce install timeout in seconds.")
    args = parser.parse_args()
    if not re.fullmatch(r"[1-9]\d*G", args.disk_size) or int(args.disk_size[:-1]) < 12:
        parser.error("--disk-size must be at least 12G, expressed in whole GiB (for example 16G).")
    if min(args.boot_timeout, args.install_timeout, args.package_timeout) < 1 or args.memory < 1024:
        parser.error("Timeouts must be positive and VM memory must be at least 1024 MiB.")
    return args


def build():
    options = arguments()
    root_password = os.environ.get("ROOT_PASSWORD", "")
    desktop_password = os.environ.get("DESKTOP_PASSWORD", "")
    for name, value in (("ROOT_PASSWORD", root_password), ("DESKTOP_PASSWORD", desktop_password)):
        if not value.isascii() or not value.isprintable() or not 1 <= len(value) <= 72:
            raise ValueError(f"{name} must be set to 1–72 printable ASCII characters.")
    output = options.output.resolve()
    if output.exists():
        raise FileExistsError(f"Output already exists: {output}")
    checkpoint = options.checkpoint.resolve() if options.checkpoint else None
    if checkpoint == output:
        raise ValueError("Output and checkpoint must be different files.")
    work = options.work_dir.resolve()
    work.mkdir(parents=True, exist_ok=True)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent, prefix=".obsd-install-") as staging:
        directory = Path(staging)
        disk = directory / "guest.qcow2"
        with (work / "serial.log").open("w") as logfile, build_server(root_password, desktop_password) as url:
            transcript = Transcript(logfile, (root_password, desktop_password))
            if checkpoint:
                package_checkpoint(checkpoint, url, root_password, options, transcript)
                # A writable overlay keeps the checkpoint intact if customization
                # fails. Flatten only the finished guest for packaging.
                overlay = directory / "customization.qcow2"
                subprocess.run(["qemu-img", "create", "-q", "-f", "qcow2", "-F", "qcow2", "-b",
                                str(checkpoint), str(overlay)], check=True)
                run_guest_stages(overlay, url, root_password, options, transcript, ("provision",))
                subprocess.run(["qemu-img", "convert", "-f", "qcow2", "-O", "qcow2",
                                str(overlay), str(disk)], check=True)
            else:
                install_new_disk(disk, url, options, transcript)
                run_guest_stages(disk, url, root_password, options, transcript, ("packages", "provision"))
        check_disk(disk)
        os.link(disk, output)
    log(f"Power-off verified; guest disk ready: {output}")


if __name__ == "__main__":
    try:
        build()
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        sys.exit(f"Build failed: {error}")
