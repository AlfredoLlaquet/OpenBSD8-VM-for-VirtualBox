"""Exercise the existing, unchanged OpenBSD Xfce download on VirtualBox itself."""
from pathlib import Path
import sys
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from verify_desktop import Guest, available_port, verify
from vbox import machine


def main():
    disk = Path(sys.argv[1]).resolve(strict=True)
    evidence = Path(sys.argv[2]).resolve()
    evidence.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as work:
        temp = Path(work)
        port = available_port()
        guest = Guest(temp, port, "OpenSesame", "CheckOut_TheCrumbs.org")
        with machine(disk, "OpenBSD", 3072, temp, port, evidence) as keyboard:
            verify(guest, keyboard, temp, evidence, "OpenSesame", time.monotonic() + 1800)


if __name__ == "__main__":
    main()
