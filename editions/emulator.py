"""Start a BIOS/SATA QEMU guest with only a loopback port for verification."""
import contextlib
import subprocess

from remote import Monitor, connect_monitor


@contextlib.contextmanager
def machine(disk, disk_format, memory, work, port, evidence, *, disposable=True):
    if disposable:
        overlay = work / "proof.qcow2"
        subprocess.run(["qemu-img", "create", "-q", "-f", "qcow2", "-F", disk_format, "-b",
                        str(disk), str(overlay)], check=True)
        disk, disk_format = overlay, "qcow2"
    monitor_path = work / "qmp"
    command = ["qemu-system-x86_64", "-machine", "pc,accel=kvm:tcg", "-cpu", "max", "-m", str(memory),
               "-smp", "2", "-display", "none", "-vga", "std", "-device", "ich9-ahci,id=sata",
               "-drive", f"if=none,id=os,file={disk},format={disk_format}",
               "-device", "ide-hd,drive=os,bus=sata.0,bootindex=1",
               "-nic", f"user,model=e1000,hostfwd=tcp:127.0.0.1:{port}-:22",
               "-qmp", f"unix:{monitor_path},server=on,wait=off",
               "-serial", f"file:{evidence / 'console.log'}", "-monitor", "none"]
    with (evidence / "qemu.log").open("w") as log:
        process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT)
        try:
            with connect_monitor(monitor_path, process) as connection:
                monitor = Monitor(connection)
                try:
                    yield monitor, process
                finally:
                    monitor.stream.close()
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
