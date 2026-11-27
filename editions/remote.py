"""Guest authentication, QMP keyboard input and polling shared by the image checks."""
import json
import os
import shlex
import socket
import subprocess
import time

import pexpect
from PIL import Image

def log(message):
    print(message, flush=True)


def redact(message):
    # Replace complete credentials before clipping output at a diagnostic size limit.
    for name in ("ROOT_PASSWORD", "DESKTOP_PASSWORD", "OLD_ROOT_PASSWORD", "OLD_DESKTOP_PASSWORD"):
        if value := os.environ.get(name):
            message = message.replace(value, "[redacted]")
    return message


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
    raise RuntimeError(f"{description} timed out. Last result: {redact(detail)[-1200:]}")


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
        for variable in ("ROOT_PASSWORD", "DESKTOP_PASSWORD", "OLD_ROOT_PASSWORD",
                         "OLD_DESKTOP_PASSWORD", "SSH_AUTH_SOCK"):
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
        detail = redact((result.stderr or result.stdout or "").strip())
        raise RuntimeError(f"{description} failed ({result.returncode}): "
                           f"{detail[-4000:]}")
    return result.stdout.strip()
