"""Launch the extracted VDI with Oracle VirtualBox and a disposable byte-for-byte copy."""
import contextlib
import os
from pathlib import Path
import subprocess
import time


def vbox(*args, timeout=90):
    return subprocess.run(["VBoxManage", *map(str, args)], check=True, text=True,
                          capture_output=True, timeout=timeout)


class Keyboard:
    def __init__(self, name):
        self.name = name

    def key(self, *names):
        codes = {"ret": "1c", "esc": "01", "backspace": "0e", "tab": "0f", "spc": "39", "shift": "2a",
                 "alt": "38", "meta_l": "e0 5b", "f1": "3b", "f2": "3c", "p": "19", "l": "26",
                 "f": "21", "w": "11", "e": "12", "b": "30", "m": "32"}
        down = [codes[name].split() for name in names]
        up = [s[:-1] + [f"{int(s[-1], 16) + 128:02x}"] for s in reversed(down)]
        vbox("controlvm", self.name, "keyboardputscancode", *[n for group in down + up for n in group])
        time.sleep(0.15)

    def type_text(self, value):
        vbox("controlvm", self.name, "keyboardputstring", value)
        time.sleep(0.2)

    def screenshot(self, unused, destination):
        vbox("controlvm", self.name, "screenshotpng", destination)


@contextlib.contextmanager
def machine(disk, system, memory, temp, port, evidence):
    # Register only an independent copy. VirtualBox can update the VDI header
    # of even an immutable parent when it first registers a qemu-img export.
    copy = temp / "desktop-test.vdi"
    subprocess.run(["cp", "--reflink=auto", "--sparse=always", "--", str(disk), str(copy)], check=True)
    name = "MVM-" + system
    os.environ["VBOX_USER_HOME"] = str(temp / "VirtualBox")
    vbox("createvm", "--name", name, "--ostype", system + "_64", "--register",
         "--basefolder", temp / "machines")
    try:
        vbox("modifyvm", name, "--memory", memory, "--cpus", "2", "--ioapic", "on", "--firmware", "bios",
             "--graphicscontroller", "vboxvga", "--vram", "128", "--accelerate-3d", "off",
             "--usb-ohci", "on", "--mouse", "usbtablet", "--nic1", "nat", "--nictype1", "82540EM",
             "--cableconnected1", "on", "--natpf1", f"check,tcp,127.0.0.1,{port},,22",
             "--boot1", "disk", "--boot2", "none", "--boot3", "none", "--boot4", "none")
        vbox("storagectl", name, "--name", "AHCI", "--add", "sata", "--controller", "IntelAhci", "--portcount", "1")
        vbox("storageattach", name, "--storagectl", "AHCI", "--port", "0", "--device", "0",
             "--type", "hdd", "--medium", copy)
        vbox("startvm", name, "--type", "headless")
        yield Keyboard(name)
    except subprocess.CalledProcessError as error:
        raise RuntimeError((error.stderr or error.stdout or str(error)).strip()) from error
    finally:
        subprocess.run(["VBoxManage", "controlvm", name, "poweroff"], capture_output=True)
        logdir = temp / "machines" / name / "Logs"
        if (logdir / "VBox.log").exists():
            (evidence / "VBox.log").write_bytes((logdir / "VBox.log").read_bytes())
        subprocess.run(["VBoxManage", "unregistervm", name], capture_output=True)
