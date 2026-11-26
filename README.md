# OpenBSD with Xfce for VirtualBox

The private release contains a ZIP with an installed OpenBSD 8.0 amd64 virtual disk. Extract the ZIP, follow `VirtualBox.txt`, and use `FIRST-LOGIN.txt` to sign in to Xfce. A fresh build generates new desktop and root passwords.

The GitHub Actions workflow installs OpenBSD in QEMU, converts the installed disk to VDI, compares the source and converted sectors, and boots the VDI with a disposable write layer to test the graphical login. It verifies the VDI checksum again before packaging it. The download is intended for VirtualBox 7.2.22 on Intel or AMD hosts.
