# OpenBSD 8 desktops for VirtualBox

Choose Xfce, GNOME, KDE Plasma, or cwm. Each download contains a separate virtual hard disk with OpenBSD 8.0 and one desktop already installed. Attach the disk in VirtualBox and sign in.

**Companion project** · [FreeBSD 15 desktops for VirtualBox](https://github.com/AlfredoLlaquet/FreeBSD15-VM-for-VirtualBox)

Created and directed by **Alfredo Llaquet-Alsina**. Implemented by **ChatGPT**.

## Choose your desktop

The original Xfce disk is downloadable. The GNOME, Plasma, and cwm disks are being built and tested.

| Edition | What you get | Starting memory | Download |
| --- | --- | ---: | --- |
| Xfce | A familiar panel, applications menu, and Thunar file manager. | 3 GB | [Download ZIP](https://github.com/AlfredoLlaquet/OpenBSD8-VM-for-VirtualBox/releases/download/openbsd-8.0-xfce-public-45953251746-1/OpenBSD-8.0-Xfce-amd64.zip) |
| GNOME | An Activities overview, searchable apps, and the Files browser. | 6 GB | [Build progress](https://github.com/AlfredoLlaquet/OpenBSD8-VM-for-VirtualBox/actions) |
| KDE Plasma | A customizable panel, Dolphin file manager, and Konsole terminal. | 6 GB | [Build progress](https://github.com/AlfredoLlaquet/OpenBSD8-VM-for-VirtualBox/actions) |
| cwm | A charcoal desktop with keyboard shortcuts, a slim panel, and a live system monitor. | 3 GB | [Build progress](https://github.com/AlfredoLlaquet/OpenBSD8-VM-for-VirtualBox/actions) |

## Set up VirtualBox

You need VirtualBox on a 64-bit Intel or AMD computer. These are x86-64 guests. VirtualBox on an Apple silicon Mac or an ARM-based Windows computer requires a different guest architecture. **Host** means your normal computer. **Guest** means the OpenBSD desktop inside the VM window.

1. **Download one edition.** On its release page, expand **Assets**. For a ZIP, extract it normally. For a numbered 7-Zip archive, download every file ending in `.7z.001`, `.002`, and so on into one folder. Open the first part with 7-Zip or an archive manager that supports split 7z files, and extract once. GitHub’s **Source code** links contain the build scripts. The extracted **`.vdi`** is the installed disk. Keep it in a permanent folder.
2. **Create the machine.** In VirtualBox Manager, click **New**, give the VM a name such as **OpenBSD Plasma**, and select **BSD → OpenBSD (64-bit)**. Leave **ISO Image** empty. Set **2 processors** and the memory shown above. Leave **EFI/UEFI** unchecked. Choose **Use an existing virtual hard disk file** if offered. Otherwise, finish the wizard and attach the disk in the next step.
3. **Attach the disk.** With the machine powered off, open **Settings → Storage**. Switch to **Expert** view if necessary. Find **Controller: AHCI** or add an **AHCI (SATA)** controller. If the wizard placed the extracted VDI under **Controller: IDE**, drag its entry onto **Controller: AHCI**. To attach it manually, select the AHCI controller, click **Add Hard Disk**, then **Add** to locate the VDI and **Choose**. Remove the attachment of any blank disk the wizard created. The downloaded VDI should be the only hard disk, on **AHCI port 0**. The empty IDE optical drive can stay where it is.
4. **Set the remaining hardware.** Use the settings in the table below. Click **OK**, select the VM, and click **Start**.
5. **Sign in as `desktop`.** Enter the password from the next section and press **Enter**. Password fields can stay blank while you type. The initial keyboard layout is US English.

| VirtualBox setting | Value |
| --- | --- |
| System → Motherboard | Legacy BIOS, I/O APIC enabled |
| System → Pointing Device | USB Tablet. Enable the USB controller if prompted. USB 1.1 (OHCI) is sufficient. |
| Display → Screen | VBoxVGA, 64 MB for the original Xfce image and 128 MB for the other editions, 3D acceleration off |
| Network → Adapter 1 | NAT, Intel PRO/1000 MT Desktop (82540EM), Cable Connected |

## Sign in and change the passwords

| Account | Public initial password | Purpose |
| --- | --- | --- |
| `desktop` | `OpenSesame` | Graphical login and everyday work |
| `root` | `CheckOut_TheCrumbs.org` | System administration through `su -` |

In a terminal, run `passwd` to change the desktop password. Then run `su -`, enter the initial root password, and run `passwd` again to set your own root password. Type `exit` to return to the desktop account. Do this before enabling incoming network access.

## Using your edition

### Xfce

Open the applications menu on the panel. Thunar manages files. **Alt+F2** opens the launcher, where you can type `xterm`. Use the logout menu to shut down.

The original Xfce disk was tested in VirtualBox 7.2.22 on a FreeBSD 15 host. Its ZIP is about **1.49 GB**. The extracted VDI initially occupies about **4.4 GB** and can grow to **16 GiB**. [Original release and offline instructions.](https://github.com/AlfredoLlaquet/OpenBSD8-VM-for-VirtualBox/releases/tag/openbsd-8.0-xfce-public-45953251746-1)

### GNOME

Press **Super** (the Windows or Command key sent to the guest) for the Activities overview. Start typing an application name to find it. **Files** opens your home folder. The system menu at the top right contains the power controls.

### KDE Plasma

Use the application launcher on the panel or press **Alt+Space** to search. **Dolphin** manages files, **Konsole** opens a terminal, and **System Settings** controls the desktop’s appearance.

### cwm

Press **Super+P**, type a program name, and press **Enter**. The bottom panel shows open windows, the notification area, and the clock. Conky displays CPU, memory, and disk usage. The active window has a thin muted-gold border. **Super+F1** opens the shortcut guide inside the VM.

| Shortcut | Action |
| --- | --- |
| Super+Enter / Super+T | Open xterm / open or reattach tmux |
| Super+E / Super+M | Open PCManFM-Qt / Midnight Commander |
| Super+B / Super+L | Open Firefox / lock the screen |
| Print Screen | Save a PNG to `~/Pictures/Screenshots` |
| Alt+Tab / Alt+Shift+Tab | Cycle windows forward / backward |
| Super+F / Super+W | Toggle full screen / close the active window |
| Super+1 through Super+4 | Show a workspace |
| Super+Shift+1 through Super+Shift+4 | Move the active window to a workspace |
| Super+Shift+Q | Log out to the greeter |

### Shut down or troubleshoot

Use the desktop’s power menu when available. From any edition, run `su -` in a terminal, enter the root password, then run `shutdown -p now`. Wait until VirtualBox reports **Powered Off** before copying a disk. Your next start retains your files and settings.

| Symptom | What to check |
| --- | --- |
| No bootable medium, or an installer starts | Attach the extracted VDI to AHCI port 0, leave the optical drive empty, and turn EFI off. |
| The desktop does not appear | Check the graphics controller, video memory, 3D setting, and the edition’s RAM. |
| The mouse is captured | Select USB Tablet. The Host key shown at the bottom of the VM window releases captured input. |
| Login fails | Check capitalization and the US keyboard layout. The root password contains both an underscore and a period. |
| No network | Recheck NAT, the Intel adapter model, and Cable Connected. |
| VirtualBox reports a duplicate disk UUID | Use VirtualBox’s **Clone** command when making an independent copy of an already registered VM. |

## Nerd Section

### Base system and disk layout

The build authenticates the complete `install80.iso` against `SHA256.sig` using the pinned OpenBSD 8.0 base signify key. It installs every distribution set, including Xenocara, from that ISO. The guest applies signed `syspatch` updates and uses `pkg_add` against the official OpenBSD 8.0/amd64 package repository. The installer uses a whole-disk MBR and an OpenBSD disklabel. The layout separates `/`, `/tmp`, `/var`, `/usr`, `/usr/local`, and `/home`, plus swap. New editions have 48 GiB of virtual capacity. The original Xfce disk has 16 GiB. Inspect a running guest with `disklabel sd0`, `df -h`, `uname -a`, and `pkg_info`.

| Session | Login and startup |
| --- | --- |
| Xfce | xenodm reads `~/.xsession` and starts Xfce with ConsoleKit. The original installation and archive have their own release history. |
| GNOME | GDM and the packaged GNOME Xorg session. System D-Bus starts before GDM. Avahi and multicast supply service discovery. |
| Plasma | xenodm, the KDE login class, ConsoleKit, a per-user runtime directory, and `startplasma-x11`. Software rendering accommodates the virtual graphics adapter. |
| cwm | Base-system xenodm and cwm, a per-session D-Bus, and the dotfiles in [guest/cwm](guest/cwm). |

The 8.0 release package collection provides GNOME Shell 49 and Plasma 6.7. The exact installed versions belong to each disk’s package inventory. OpenBSD supplies cwm, xenodm, xterm, xlock, and tmux with the system. Firefox, Geany, the Qt file manager, and the remaining cwm applications come from packages.

### Network, maintenance, and integration

`/etc/hostname.em0` contains `inet autoconf`. Each VM gets an address behind NAT. Root SSH login is disabled. SSH is enabled inside the guest, and the recommended VirtualBox configuration has no incoming port forwards. The provisioning step discards SSH host keys and DHCP state so copies get fresh identities on first boot. Use `su -` from the wheel account for administration.

Run `syspatch` and `pkg_add -u` as root to maintain the installed release. Follow reboot instructions from `syspatch`. The build waits for kernel relinking and checks `/bsd` against the recorded checksum before it powers off. OpenBSD has no Oracle Guest Additions. USB Tablet provides absolute pointer input. For file transfer, use a separately configured network service. The guest’s display settings control the available resolutions.

### The cwm environment

| Function | Programs and configuration |
| --- | --- |
| Shell and navigation | cwm, dmenu, tint2, xterm, tmux, PCManFM-Qt, Midnight Commander |
| Background and X11 services | feh, picom with `backend = "xrender"`, X11 Conky, dunst, xlock, scrot, Parcellite |
| Reading, editing, and media | Vim, Geany, Firefox, Zathura with the Poppler PDF plugin, mpv, Fastfetch |
| Appearance | JetBrains Mono, LXAppearance, dark Adwaita GTK and Qt styles, charcoal surfaces, muted-gold focus, green terminal text |

The session script loads X resources, starts the daemons, paints the wallpaper, and hands control to cwm. Adjust shortcuts in `~/.cwmrc`, the panel in `~/.config/tint2/tint2rc`, Conky in `~/.config/conky/conky.conf`, and the compositor in `~/.config/picom/picom.conf`. Parcellite manages the guest’s X11 clipboard. The keyboard guide is installed under `/usr/local/share/mvm/`.

### Build, verification, and checksums

The package stage boots the official system with QEMU, installs packages, and saves a powered-off QCOW2 checkpoint per edition. The release stage configures that edition, exports a standalone, dynamically allocated VDI, and compares its guest-visible sectors with the source. The QA runner uses a disposable write layer so the verification login cannot alter the delivered disk. Each new edition’s release includes an inventory, screenshots, a verification report, and the archive checksums. The report identifies the hypervisor and RAM actually exercised.

For a numbered archive, download its checksum file and all volumes to one directory. On Linux use `sha256sum -c SHA256SUMS-downloads.txt`. On FreeBSD and OpenBSD use `sha256 filename`, on macOS use `shasum -a 256 filename`, and in Windows PowerShell use `Get-FileHash .\filename -Algorithm SHA256`. Compare the 64 hexadecimal digits. The extracted `SHA256SUMS` contains the hash of the VDI. Check it **before the first boot**, which writes to the disk.

The original Xfce ZIP has its own [ZIP checksum](https://github.com/AlfredoLlaquet/OpenBSD8-VM-for-VirtualBox/releases/download/openbsd-8.0-xfce-public-45953251746-1/OpenBSD-8.0-Xfce-amd64.zip.sha256) and an internal VDI checksum. Its archived installation guide remains specific to that image. The manual **Build OpenBSD Xfce** and **Update existing OpenBSD disk** workflows preserve its original build and refresh paths.

To rebuild, use **Actions → Prepare desktop packages**, choose an edition, then use the edition release workflow with that preparation run’s ID. Desktop packages and base updates can change between builds. GitHub release assets hold the large downloads. Normal README edits do not initiate a VM build.

Further reading: [OpenBSD documentation](https://www.openbsd.org/faq/), [VirtualBox 7.2 User Guide](https://docs.oracle.com/en/virtualization/virtualbox/7.2/user/).

## License

The project’s original scripts, workflows, configuration, and documentation use the [Unlicense](LICENSE). The operating system and bundled applications retain their individual licenses. [Third-party notices](THIRD-PARTY-NOTICES.txt).

### Alfredo Llaquet-Alsina is not only a BSD enthusiast, but also a writer. Please visit [www.TheCrumbs.org](https://www.thecrumbs.org/) and take a look at his work, free for everyone.
