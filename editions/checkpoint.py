#!/usr/bin/env python3
"""Install an edition's OpenBSD packages and save the clean, powered-off intermediate disk."""
import argparse
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import build_guest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("edition", choices=["cwm", "gnome", "plasma"])
    parser.add_argument("work_dir", type=Path)
    options = parser.parse_args()
    options.work_dir = options.work_dir.resolve()
    options.work_dir.mkdir(parents=True, exist_ok=True)
    options.disk_size = "48G"
    options.memory = 6144
    options.accel = "auto"
    options.boot_timeout = 900
    options.install_timeout = 5400
    options.package_timeout = 10800
    root = os.environ["ROOT_PASSWORD"]
    desktop = os.environ["DESKTOP_PASSWORD"]
    with (options.work_dir / "serial.log").open("w") as log:
        transcript = build_guest.Transcript(log, (root, desktop))
        with build_guest.build_server(root, desktop, options.edition) as url:
            build_guest.package_checkpoint(options.work_dir / "packages.qcow2", url, root, options, transcript)


if __name__ == "__main__":
    main()
