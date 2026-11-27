#!/usr/bin/env python3
"""Cold-boot a protected VDI, type into its real greeter, and exercise the selected desktop."""
import argparse
from pathlib import Path
import secrets
import shlex
import subprocess
import tempfile
import time

from PIL import Image, ImageFilter

import emulator
import vbox
from remote import Guest, available_port, checked, wait_for

PATH = "export PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/X11R6/bin:/usr/local/bin:/usr/local/sbin; "
XLOGIN = r"""
export DISPLAY=:0
auth=$(ps axww -o command= | awk '/[X]org |[\/]X :0/ {for(i=1;i<NF;i++) if($i=="-auth") print $(i+1)}')
for cookie in $auth /etc/X11/xenodm/authdir/authfiles/* /var/run/xenodm/authdir/authfiles/* /var/lib/xdm/authdir/authfiles/* /var/db/xdm/authdir/authfiles/*; do
    [ -f "$cookie" ] || continue
    XAUTHORITY="$cookie" xwininfo -root -tree 2>/dev/null | grep -i '"xlogin"' && exit 0
done
exit 1
"""
GDM = r"""
for account in _gdm gdm; do
    uid=$(id -u "$account" 2>/dev/null) || continue
    pgrep -x -u "$uid" gnome-shell && exit 0
done
exit 1
"""
CWM_APPS = """cwm dmenu_run tint2 xterm pcmanfm-qt mc picom conky feh dunst xlock scrot
parcellite tmux lxappearance vim geany firefox zathura mpv fastfetch fc-match"""
PROCESSES = {"xfce": ["xfce4-session", "xfwm4", "xfce4-panel", "xfdesktop"],
             "gnome": ["gnome-shell"], "plasma": ["plasmashell"], "cwm": ["cwm", "tint2", "picom", "conky", "dunst", "parcellite"]}


def processes(programs):
    names = " ".join(programs)
    return f'for p in {names}; do pgrep -x -u "$(id -u)" "$p" >/dev/null || {{ echo "Waiting for $p"; exit 1; }}; done; echo "{names}"'


def verify(args, guest, keyboard, evidence):
    record = [f"{args.system} / {args.edition} / {args.memory} MiB / {args.backend}"]
    def save(message):
        record.append(message)
        (evidence / "verification.txt").write_text("\n".join(record) + "\n")
        print(message, flush=True)

    def user(command):
        return guest.run(PATH + command, timeout=35)

    def must(command):
        return checked(user(command), command)

    def until(label, probe, seconds):
        return wait_for(label, probe, time.monotonic() + seconds, pause=4)

    def greeter():
        code = GDM if args.edition == "gnome" else XLOGIN
        return until("Waiting for graphical login", lambda: guest.root(PATH + code, 30), 260)

    def snap(name):
        # GDM replaces the greeter X server during login. VirtualBox can report
        # a disabled framebuffer, or return a black frame, during this transition.
        target = evidence / f"{name}.png"
        deadline = time.monotonic() + 95
        while time.monotonic() < deadline:
            try:
                keyboard.screenshot(evidence / "screen.ppm", target)
                with Image.open(target) as frame:
                    preview = frame.convert("L").resize((240, 160))
                edges = preview.filter(ImageFilter.FIND_EDGES).crop((2, 2, 238, 158))
                if sum(edges.histogram()[20:]) >= 60:
                    (evidence / "screen.ppm").unlink(missing_ok=True)
                    return
            except (OSError, subprocess.CalledProcessError):
                pass
            keyboard.key("shift")
            time.sleep(3)
        raise RuntimeError(f"No painted {name} screen on the virtual monitor within 95 seconds")

    start = until("Cold boot and SSH authentication", lambda: user("sysctl -n kern.boottime"), 850)
    if must("id -un") != "desktop" or checked(guest.root("id -u", 45), "root login") != "0":
        raise RuntimeError("Initial account verification failed")
    save("Both initial accounts authenticated. " + must("uname -srm"))
    if must("uname -s") != args.system or must("uname -m") != "amd64":
        raise RuntimeError("Unexpected OS or architecture")
    if args.system == "OpenBSD" and must("uname -r") != "8.0":
        raise RuntimeError("Unexpected OpenBSD release")
    if args.system == "FreeBSD" and not must("freebsd-version -u").startswith("15.1-RELEASE"):
        raise RuntimeError("Unexpected FreeBSD release")
    inventory = "pkg_info -q" if args.system == "OpenBSD" else "pkg query '%n-%v'"
    (evidence / "PACKAGES.txt").write_text(must(inventory + " | sort") + "\n")
    save(must("df -h; sysctl hw.physmem"))
    greeter()
    snap("before-login")
    names = PROCESSES[args.edition].copy()
    if args.edition == "plasma":
        names.append("kwin_x11" if args.system == "OpenBSD" else "kwin_wayland")
    must(f'! pgrep -x -u "$(id -u)" {names[0]} >/dev/null')
    # GDM appears as soon as its process starts. Wait for the interactive greeter.
    if args.edition == "gnome":
        time.sleep(8)
    keyboard.type_text("desktop")
    keyboard.key("ret")
    time.sleep(1.5)
    keyboard.type_text("OpenSesame")
    keyboard.key("ret")
    try:
        save("Graphical login started " + until("Checking the logged-in desktop", lambda: user(processes(names)), 300))
    except RuntimeError:
        print(must('tail -60 "$HOME/.xsession-errors" 2>/dev/null || true'), flush=True)
        raise
    time.sleep(4)
    snap("desktop")
    if args.smoke:
        save("Lower-memory boot, graphical login and desktop processes passed.")
        return
    if args.edition == "cwm":
        commands = " ".join(CWM_APPS.split())
        save(must(f'for p in {commands}; do command -v "$p" || exit 1; done; '
                  'fc-match -f "%{family}\\n" "JetBrains Mono" | grep -Fi "JetBrains Mono"; '
                  'grep -Eq \'backend[[:space:]]*=[[:space:]]*"xrender"\' "$HOME/.config/picom/picom.conf"; '
                  'find /usr/local/lib -name "*pdf-poppler*" | grep .'))
        keyboard.key("meta_l", "e")
        until("Checking the PCManFM-Qt keyboard shortcut", lambda: user(processes(["pcmanfm-qt"])), 75)
        keyboard.key("meta_l", "ret")
    else:
        keyboard.key("alt", "f2")
        time.sleep(2)
        keyboard.type_text("xterm")
        keyboard.key("ret")
    until("Checking the terminal launched from the graphical desktop", lambda: user(processes(["xterm"])), 95)
    time.sleep(2)
    marker = "/tmp/mvm-proof-" + secrets.token_hex(5)
    keyboard.type_text(f"tty > {marker} && id -un >> {marker}")
    keyboard.key("ret")
    save("Interactive xterm: " + until("Checking the interactive GUI terminal", lambda:
         user(f"grep -Fx desktop {marker} >/dev/null && grep '^/dev/' {marker}"), 75))
    snap("terminal")
    if args.edition == "cwm":
        keyboard.key("meta_l", "l")
        until("Checking xlock", lambda: user(processes(["xlock"])), 40)
        time.sleep(2)
        keyboard.key("spc")
        snap("unlock-prompt")
        keyboard.key("backspace")
        keyboard.type_text("OpenSesame")
        keyboard.key("ret")
        until("Unlock with the desktop password", lambda: user('! pgrep -x -u "$(id -u)" xlock >/dev/null'), 45)
        save("cwm shortcuts launched the file manager and terminal, then locked and unlocked the session.")
    net = ("ftp -V -w 20 -o /dev/null https://cdn.openbsd.org/pub/OpenBSD/8.0/amd64/SHA256"
           if args.system == "OpenBSD" else
           "fetch -T 20 -qo /dev/null https://download.freebsd.org/releases/VM-IMAGES/15.1-RELEASE/amd64/Latest/CHECKSUM.SHA256")
    save(until("Checking DHCP, default route and outgoing HTTPS", lambda:
         user("ifconfig em0 | grep 'inet ' && route -n get default | grep 'gateway:' && " + net), 110))
    guest.root("shutdown -r now", 90)
    new = until("Waiting for a distinct second boot", lambda:
                user(f'b=$(sysctl -n kern.boottime); [ -n "$b" ] && [ "$b" != {shlex.quote(start)} ] && echo "$b"'), 800)
    greeter()
    save(f"Reboot returned to graphical login. First boot {start}. Second boot {new}.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--system", choices=["OpenBSD", "FreeBSD"], required=True)
    parser.add_argument("--edition", choices=list(PROCESSES), required=True)
    parser.add_argument("--backend", choices=["virtualbox", "qemu"], required=True)
    parser.add_argument("--memory", type=int, required=True)
    parser.add_argument("--disk", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    evidence = args.evidence.resolve()
    evidence.mkdir(parents=True, exist_ok=True)
    disk = args.disk.resolve(strict=True)
    with tempfile.TemporaryDirectory() as directory:
        work = Path(directory)
        port = available_port()
        guest = Guest(work, port, "OpenSesame", "CheckOut_TheCrumbs.org")
        backend = (vbox.machine(disk, args.system, args.memory, work, port, evidence)
                   if args.backend == "virtualbox" else emulator.machine(disk, "vdi", args.memory, work, port, evidence))
        with backend as control:
            keyboard = control[0] if isinstance(control, tuple) else control
            try:
                verify(args, guest, keyboard, evidence)
            except Exception:
                try:
                    keyboard.key("shift")
                    time.sleep(1)
                    keyboard.screenshot(work / "failure.ppm", evidence / "failure.png")
                except Exception as err:
                    print("Virtual monitor at failure:", str(err), flush=True)
                try:
                    diag = guest.root(PATH + 'ps axww; for f in /var/log/xdm.log /var/log/xenodm.log /var/log/gdm.log /var/log/gdm/*log /var/log/Xorg.0.log /home/desktop/.xsession-errors /home/desktop/.cache/gdm/session.log /var/log/messages; do [ ! -f "$f" ] || { echo "$f"; tail -55 "$f"; }; done', 65)
                    (evidence / "guest-diagnostics.txt").write_text(diag.stdout)
                    print(diag.stdout[-12000:], flush=True)
                except Exception as err:
                    print("Guest diagnostics:", type(err).__name__, flush=True)
                raise


if __name__ == "__main__":
    main()
