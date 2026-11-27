# OpenBSD 8 with Xfce for VirtualBox

A ready-to-go OpenBSD/Xfce virtual disk image for VirtualBox.

OpenBSD 8.0 and the Xfce desktop are already installed. Download the disk, create a virtual machine using the settings below, and sign in. You do not need to install OpenBSD or Xfce yourself.

Created and directed by **Alfredo Llaquet-Alsina**. Implemented by **ChatGPT**.

**[Download the virtual disk ZIP](https://github.com/AlfredoLlaquet/OpenBSD8-VM-for-VirtualBox/releases/latest/download/OpenBSD-8.0-Xfce-amd64.zip)** · [Download the complete instructions](https://github.com/AlfredoLlaquet/OpenBSD8-VM-for-VirtualBox/releases/latest/download/OpenBSD8-VM-for-VirtualBox-INSTRUCTIONS.txt) · [All releases](https://github.com/AlfredoLlaquet/OpenBSD8-VM-for-VirtualBox/releases)

The ZIP contains the installed `.vdi` disk, `OpenBSD8-VM-for-VirtualBox-INSTRUCTIONS.txt`, license notices, and `SHA256SUMS`. The instructions include both initial passwords and can be read without an Internet connection.

## Compatibility

**Tested with VirtualBox 7.2.22 on a FreeBSD 15 host.**

The image is expected to work with other VirtualBox 7.x releases on Intel/AMD x86-64 computers running VirtualBox, including Windows, Linux, Intel-based macOS, and FreeBSD. Other VirtualBox versions and host operating systems have not been tested. Later major VirtualBox releases may also work, but compatibility is not guaranteed in advance.

The guest architecture is **amd64**, also called **x86-64** or **x64**. This includes compatible 64-bit Intel processors as well as AMD processors. It does **not** include ARM processors: VirtualBox on Apple silicon Macs or Windows ARM computers cannot run this x86-64 image. See Oracle's [host architecture limitations](https://docs.oracle.com/en/virtualization/virtualbox/7.2/user/installation.html).

VirtualBox must be installed on your computer, with hardware virtualization enabled. The recommended memory allocation for the virtual machine is **3 GB of RAM**. VirtualBox itself is not included in the download.

The extracted VDI file initially occupies approximately **4.4 GB of disk space** on your computer. Its file size grows as data is written inside the virtual machine. The virtual disk has a total capacity of **16 GiB (about 17.2 GB)**.

## Installation Instructions

Here, **host** means your normal computer and its operating system. **Guest** means the OpenBSD system running inside the VirtualBox window. Do the following setup on the host.

### 1. Download and extract the disk

1. Use **Download the virtual disk ZIP** above. Alternatively, open **All releases**, find the current release, expand **Assets** if necessary, and download `OpenBSD-8.0-Xfce-amd64.zip`.
2. Extract the ZIP into a permanent folder where you want to keep the VM's disk. On Windows, right-click the ZIP and choose **Extract All**. On other systems, use your archive manager's extraction command.
3. Find `OpenBSD-8.0-Xfce-amd64.vdi` in the extracted files. This is the installed disk that VirtualBox will use. Keep it in that folder after attaching it to the VM.

The **Source code (zip)** and **Source code (tar.gz)** downloads on the release page contain the project's build scripts, not the installed operating system. The `.vdi` is a disk image, so it is attached to a new VM using the steps below; it is not an ISO installer or an appliance for **Import Appliance**.

Download verification is explained under **Checksums** in the Nerd Section.

### 2. Create a virtual machine

1. Open **VirtualBox Manager** and click **New**.
2. Give the machine a name, such as **OpenBSD 8 Xfce**. Choose the **BSD** operating-system family and **OpenBSD (64-bit)**. Depending on your VirtualBox version, these choices may be labeled **Type**, **OS**, **Version**, or **OS Version**.
3. Leave **ISO Image** empty. No installation media or unattended installation is needed.
4. Set the memory to **3072 MB** and the processor count to **2**. Leave enough memory and processing capacity for the host.
5. Use **legacy BIOS**: leave **Enable EFI**, **UEFI**, or **Use EFI** unchecked.
6. If the wizard offers **Use an existing virtual hard disk file**, choose it and select the extracted `.vdi`. If it does not offer this choice, finish creating the VM and attach the existing disk in the next step. A blank disk created by the wizard is not needed.

Do not start the machine yet. Select it in VirtualBox Manager and open **Settings**. Some VirtualBox versions hide detailed settings until you switch from **Basic** to **Expert** view.

### 3. Check the hardware settings

Make these changes while the VM is fully powered off.

| Settings location | Value |
| --- | --- |
| System → Motherboard | EFI/UEFI off; I/O APIC on |
| System → Processor | 2 processors |
| System → Motherboard → Pointing Device | **USB Tablet** |
| Display → Screen → Graphics Controller | **VBoxVGA** |
| Display → Screen → Video Memory | **64 MB** |
| Display → Screen → Enable 3D Acceleration | Off |
| Network → Adapter 1 | Enabled; **NAT** |
| Network → Adapter 1 → Advanced → Adapter Type | **Intel PRO/1000 MT Desktop (82540EM)** |
| Network → Adapter 1 → Cable Connected | On |

For storage, select **Storage** in the same settings window:

1. Find the **AHCI (SATA) controller**, shown as **Controller: AHCI**. If it is missing, use the controller-add button to add an **AHCI (SATA)** controller.

2. Find `OpenBSD-8.0-Xfce-amd64.vdi` in the storage list. If VirtualBox attached it automatically to **Controller: IDE**, **drag the disk’s entry onto Controller: AHCI**. If it is already beneath AHCI, leave it there.

3. If the OpenBSD disk is not attached, select the AHCI controller, click **Add Hard Disk**, and choose an existing disk. In the disk selector, select the OpenBSD VDI. If it is not listed, click **Add** to locate it, then select it and click **Choose**.

4. If the wizard also created a blank hard disk, select that blank disk and choose **Remove Attachment**. The OpenBSD VDI should be the only attached hard disk.

5. Select the OpenBSD VDI and confirm that it is attached to **port 0 of the AHCI controller**.

**The IDE controller and its empty virtual CD/DVD drive can remain as they are.** Neither needs to be moved or removed. The optical drive should show **Empty**; no ISO or installation disc is needed.

The **USB Tablet** setting lets the pointer move between the host and the OpenBSD guest without the usual mouse capture. No physical tablet is needed. If VirtualBox asks you to enable a USB controller, enable it under **Settings → USB**; the basic **USB 1.1 (OHCI)** controller is sufficient for this pointing device.

Click **OK** to save the settings.

### 4. Start OpenBSD and sign in

Select the VM and click **Start**. Wait for OpenBSD to boot and display its graphical login screen. Sign in with the regular `desktop` account:

| Account | Initial password | Purpose |
| --- | --- | --- |
| `desktop` | `OpenSesame` | Normal graphical login and everyday use |
| `root` | `CheckOut_TheCrumbs.org` | System administration through `su -` |

Passwords are case-sensitive. The initial keyboard layout is US English. The password field may show no characters as you type; enter the password and press **Enter**. Your session opens Xfce.

These are public initial passwords; change both after your first login. The commands are given under **Accounts and administration** below.

Use the Xfce applications menu to open programs. To open a terminal directly, press **Alt+F2**, type `xterm`, and press **Enter**. Normal work should use the `desktop` account; the root account is for administrative commands.

### 5. Shut down and start again

Use Xfce's logout/shutdown dialog and select **Shut Down**. Wait until the VM window closes or VirtualBox reports **Powered Off** before copying the disk or changing its hardware settings. The next time you want to use it, select the VM in VirtualBox Manager and click **Start**; the disk retains your files and changes.

If the desktop's shutdown choice is unavailable, open a terminal, run `su -`, enter the root password, and then run `shutdown -p now`.

### Common setup problems

- **No bootable medium or an installer starts:** check that the extracted OpenBSD `.vdi` is attached to SATA Port 0, the optical drive is empty, and EFI/UEFI is off.
- **The VM starts but no desktop appears:** recheck **VBoxVGA**, **64 MB** video memory, and disabled 3D acceleration. Allow the boot to finish before changing anything.
- **The mouse is captured:** power off the VM and select **USB Tablet** as described above. VirtualBox displays its current **Host key** at the bottom of the VM window; pressing it releases captured input.
- **The password is rejected:** check capitalization and the US English keyboard layout. In particular, the root password contains an underscore and a period.
- **No Internet access:** recheck NAT, the Intel PRO/1000 MT Desktop adapter, and **Cable Connected**. The guest obtains its network settings automatically.
- **VirtualBox reports a duplicate disk UUID:** another copy of this disk is already registered. Use VirtualBox's cloning tools to create a separate VM rather than registering a file-manager copy of the same disk.

## Nerd Section.

### Image and virtual hardware

The download is a standalone VirtualBox **VDI** containing OpenBSD **8.0/amd64**, the OpenBSD X Window System sets, and Xfce. The fresh-build script installs all OpenBSD distribution sets and obtains desktop packages from the official OpenBSD package mirror. This is an independently prepared image, not an official OpenBSD or Oracle image.

| Component | Configuration |
| --- | --- |
| Disk | Standalone VDI, 16 GiB virtual capacity |
| Partitioning | Whole-disk MBR with an OpenBSD disklabel; unencrypted |
| Filesystems | Separate `/`, `/tmp`, `/var`, `/usr`, `/usr/local`, and `/home`; 512 MiB swap |
| Firmware | Legacy BIOS |
| Recommended VM resources | 3072 MB RAM and 2 virtual CPUs |
| Storage attachment | SATA/AHCI, port 0; OpenBSD system disk `sd0` |
| Graphics | VBoxVGA, 64 MB video memory, 3D acceleration off |
| Pointing device | Virtual USB Tablet |
| Network | NAT with an emulated Intel PRO/1000 MT Desktop adapter |
| Guest network interface | `em0`, IPv4 automatic configuration |
| Hostname | `obsd-xfce` |
| Timezone | UTC |
| Initial keyboard layout | US English |
| Graphical login | `xenodm` |
| Desktop session | Xfce, started by `/home/desktop/.xsession` |

The partitioning template assigns space to each filesystem rather than placing everything in one root filesystem. The exact free space varies with the installed packages and later use. Run `df -h` inside the guest to see the mounted filesystems and available space; root can inspect the disklabel with `disklabel sd0`.

The VDI contains the guest's disks, not VirtualBox's host-side VM settings. RAM, processor count, graphics, networking, and USB Tablet are therefore selected when the VM is created. The guest uses the graphical console; the build's temporary serial-console setup is switched back before packaging.

### Desktop and session services

The package stage requests `xfce`, `dbus`, `consolekit2`, and `polkit`, along with their dependencies. The system enables `messagebus`, `xenodm`, and `sshd`. Xfce starts through `startxfce4 --with-ck-launch` when ConsoleKit is available, and uses the ordinary `startxfce4` launcher otherwise.

To inspect the installed system, run these commands in a guest terminal:

```sh
uname -sr
machine -a
xfce4-session --version
pkg_info
df -h
```

The image carries the versions installed when it was prepared. A new build can receive newer packages or system patches, so a fixed Xfce package version is not implied by the repository name. Releases that include `IMAGE-INFO.txt` provide an inventory captured from that disk, including the installed system and packages.

### Accounts and administration

`desktop` belongs to the `wheel` group and can use `su -` with the root password. Direct root login through SSH is disabled. The documented administrative route is `su -`; no `sudo` or custom `doas` setup is required.

To change the regular account password, open a guest terminal as `desktop` and run:

```sh
passwd
```

Enter the current desktop password, then enter the new one twice. To change the root password, run:

```sh
su -
passwd
exit
```

At the `su -` prompt, enter the current root password. The following `passwd` command changes root's password because the shell is then running as root. `exit` returns to the regular desktop shell. These changes affect your own copy of the disk.

### Networking and SSH

`/etc/hostname.em0` contains `inet autoconf`. With the documented NAT configuration, VirtualBox supplies the guest's IPv4 address and outgoing network access. No port forwarding is needed for ordinary Internet use.

The SSH server runs inside the guest, but the documented NAT setup does not forward a host port to it. A deliberate port-forwarding or bridged-network setup is needed for incoming SSH connections. That configuration is separate from the normal desktop installation instructions.

The image preparation removes generated SSH host keys and the saved DHCP lease before delivery, so OpenBSD creates fresh host keys and obtains network settings when a copy first boots. A new VirtualBox VM can use its own generated network MAC address.

### Host and guest integration

OpenBSD does not have the Oracle Guest Additions provided for Windows and Linux. VirtualBox shared folders, host/guest clipboard sharing, drag and drop, and automatic desktop resizing through those additions are therefore not provided by this image. Network-based file transfer is an alternative; it requires its own network setup.

USB Tablet works independently of Guest Additions. VirtualBox translates the host pointer's position into absolute tablet coordinates, avoiding the usual relative-mouse capture. See Oracle's [pointing-device documentation](https://docs.oracle.com/en/virtualization/virtualbox/7.2/user/working-with-vms.html).

For a different display size, use Xfce's display settings and the resolutions offered by the guest's graphics driver. Changing VirtualBox's window size alone does not guarantee that the OpenBSD desktop resolution will change.

### Updates and maintenance

Open a terminal and enter a root shell with `su -`. To apply available OpenBSD 8.0 binary patches and update installed packages from the configured mirror, run:

```sh
syspatch
pkg_add -u
```

Follow any reboot instructions printed by `syspatch`. If it reports that kernel relinking is in progress, wait for that process to finish and retry. These commands maintain the installed OpenBSD release; upgrading to a different OpenBSD release is a separate operation described in the [OpenBSD FAQ](https://www.openbsd.org/faq/).

The package mirror is recorded in `/etc/installurl`. The build selects `https://cdn.openbsd.org/pub/OpenBSD`. For a backup, shut down the guest completely and copy its VM folder together with the attached VDI, or use VirtualBox's cloning and snapshot facilities. A snapshot is useful before an update but is not a separate backup of the host's storage.

### Checksums

The release provides `OpenBSD-8.0-Xfce-amd64.zip.sha256` for the downloaded ZIP. Inside the ZIP, `SHA256SUMS` records the checksum of `OpenBSD-8.0-Xfce-amd64.vdi`. These are different files and have different checksums.

Download the [ZIP checksum file](https://github.com/AlfredoLlaquet/OpenBSD8-VM-for-VirtualBox/releases/latest/download/OpenBSD-8.0-Xfce-amd64.zip.sha256) next to the ZIP. On Linux, run this in the download directory:

```sh
sha256sum -c OpenBSD-8.0-Xfce-amd64.zip.sha256
```

On FreeBSD or OpenBSD, run `sha256 OpenBSD-8.0-Xfce-amd64.zip`; on macOS, run `shasum -a 256 OpenBSD-8.0-Xfce-amd64.zip`. On Windows, open PowerShell in the download folder and run:

```powershell
Get-FileHash .\OpenBSD-8.0-Xfce-amd64.zip -Algorithm SHA256
```

Compare the resulting 64-character hash with the one in the downloaded `.sha256` file. The Linux check should report `OK`. A mismatch means the file does not match that release; download it again before using it.

To check the extracted disk, use the same SHA-256 command for `OpenBSD-8.0-Xfce-amd64.vdi` and compare it with `SHA256SUMS`. On Linux, `sha256sum -c SHA256SUMS` performs that comparison. Check the VDI **before its first normal boot**: OpenBSD writes to the disk during use, so its checksum will subsequently change.

### How the image is prepared and verified

The repository contains the build and verification scripts. Fresh builds run on an Ubuntu GitHub Actions runner and install OpenBSD under QEMU. `build_guest.py` obtains `install80.iso` and `SHA256.sig` from the official OpenBSD mirrors and authenticates the ISO with OpenBSD's `signify` signature and the pinned OpenBSD 8.0 base key before booting it.

The unattended installation creates the system and accounts. `guest/packages.sh` applies available signed binary patches and installs the desktop packages. `guest/provision.sh` configures graphical login, session services, networking, and root SSH policy; it also waits for OpenBSD's kernel relinking to finish and checks the resulting kernel before shutdown.

The fresh build uses QCOW2 as an intermediate disk format. It exports a standalone VDI with `qemu-img` and compares the guest-visible sectors of the source and exported disks. The downloadable VDI has no dependency on an intermediate QCOW2 file or backing image.

`verify_desktop.py` cold-boots the VDI under QEMU with a disposable write layer. It authenticates the desktop account, checks the graphical login, signs into Xfce through simulated keyboard input, verifies the Xfce processes and window manager, opens an interactive X terminal, checks outgoing HTTPS, and reboots to verify that the graphical login returns. Administrative checks authenticate through `su`, exercising the root password too. Screenshots and a verification report are retained by the workflow.

The disposable layer keeps those verification sessions out of the delivered VDI. The packaging step checks the original VDI checksum again, creates the ZIP, tests the ZIP archive, and generates a checksum for the final download. QEMU verification and the reported VirtualBox test are distinct: the automated checks do not claim to test every VirtualBox version or host operating system.

For this public release, the existing installed image is updated with the documented public passwords and repackaged with the consolidated instructions. Updating an existing image preserves its installed system; it is different from requesting a fresh installation from the official media. The maintained build path uses the same documented initial credentials for subsequent builds.

### Maintainer workflows

Both workflows are started manually from the repository's **Actions** tab. Source or documentation commits do not automatically rebuild the disk.

The GitHub Actions workflow **Build OpenBSD Xfce for VirtualBox** (`.github/workflows/build.yml`) creates a fresh installation from the official OpenBSD media. Its scripts install the packages, configure the guest, verify the exported disk, and package the release.

The workflow **Update existing OpenBSD disk** (`.github/workflows/refresh.yml`) starts from an existing release disk and updates its credentials and documentation. It preserves the installed operating system and packages, captures `IMAGE-INFO.txt`, then verifies and packages the resulting disk. This is the path used to prepare the existing image for its public release.

The maintained source is in this repository; the large disk download is attached to a GitHub release rather than stored as a normal Git source file. Release checksums belong to their corresponding release assets. A replacement disk requires new checksums and matching installation notes.

### Further reference

- [OpenBSD website and documentation](https://www.openbsd.org/)
- [OpenBSD FAQ](https://www.openbsd.org/faq/)
- [Xfce documentation](https://docs.xfce.org/)
- [VirtualBox 7.2 user guide](https://docs.oracle.com/en/virtualization/virtualbox/7.2/user/)

## License

This project's original scripts, configuration, workflows, and documentation are released under the [Unlicense](LICENSE). OpenBSD, Xfce, and the other software inside the disk retain their own licenses and copyright notices; see [third-party notices](THIRD-PARTY-NOTICES.txt).

<br>

### Alfredo Llaquet-Alsina is not only a BSD enthusiast, but also a writer. Please visit [www.TheCrumbs.org](https://www.thecrumbs.org/) and take a look at his work, free for everyone.
