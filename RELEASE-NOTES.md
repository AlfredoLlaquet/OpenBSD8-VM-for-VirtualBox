Download **OpenBSD-8.0-Xfce-amd64.zip**, extract it, and follow **OpenBSD8-VM-for-VirtualBox-INSTRUCTIONS.txt**. The ZIP contains the installed OpenBSD 8.0 amd64 VDI and Xfce desktop. The automatically generated source-code archives contain the build scripts, not the virtual disk.

| Account | Initial password |
| --- | --- |
| `desktop` | `OpenSesame` |
| `root` | `CheckOut_TheCrumbs.org` |

Change both initial passwords after your first login. For ordinary desktop use, sign in as `desktop`.

In VirtualBox, select **Settings → System → Motherboard → Pointing Device → USB Tablet** so the pointer can move between host and guest without the usual mouse capture.

The image configuration has been tested with VirtualBox 7.2.22 on FreeBSD 15. Other VirtualBox 7.x releases and Intel/AMD x86-64 hosts are expected to work but remain untested. ARM hosts, including Apple silicon Macs, cannot run this amd64 image through VirtualBox.

Before packaging, the published VDI was cold-booted under QEMU with a disposable write layer. Verification covered both account credentials, graphical login, the Xfce desktop, an interactive X terminal, outbound networking, and reboot. Its SHA-256 checksum was checked again after verification. The `.zip.sha256` file checks the download; `SHA256SUMS` inside the archive checks the extracted VDI.

Created and directed by **Alfredo Llaquet-Alsina**. Implemented by **ChatGPT**.
