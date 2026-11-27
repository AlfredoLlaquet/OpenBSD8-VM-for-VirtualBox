"""Write a self-contained, printable guide for exactly one downloaded disk."""
import sys

system, edition, memory, disk = sys.argv[1:]
desktop = {"xfce": "Xfce", "gnome": "GNOME", "plasma": "KDE Plasma", "cwm": "cwm"}[edition]
print(f"""{system} with {desktop} for VirtualBox 7.2.22

Created and directed by Alfredo Llaquet-Alsina. Implemented by ChatGPT.

1. Download all {disk}.7z volumes into one folder. Open the .001 file with
   7-Zip and extract once. Keep {disk}.vdi in a permanent location.
2. On an Intel/AMD x86-64 host, select New in VirtualBox, then BSD and
   {system} (64-bit). Leave ISO Image empty. Use {memory} MB of memory and two
   processors. Leave EFI off. Select the extracted disk if the wizard offers
   an existing-disk option.
3. With the VM powered off, open Settings (Expert view if necessary).
   In Storage, attach the VDI to Controller: AHCI, SATA port 0. If it is
   on IDE, drag its entry onto AHCI. Remove the attachment of any blank
   hard disk. The empty IDE optical drive can remain attached.
4. Choose VBoxVGA, 128 MB of video memory, and 3D acceleration off. Enable
   I/O APIC and select USB Tablet. Basic USB 1.1 (OHCI) is sufficient.
   Use NAT, Intel PRO/1000 MT Desktop (82540EM), and Cable Connected.
5. Start the VM and sign in using the US keyboard layout.

   Desktop account: desktop      Initial password: OpenSesame
   Administrator:   root         Initial password: CheckOut_TheCrumbs.org

Use the desktop account for daily work. Open a terminal and run passwd to
change its public password. Run su -, supply the initial root password, then
run passwd to change that password too. Type exit to leave the root shell.

To shut down from any edition, run su -, then shutdown -p now. Wait for
VirtualBox to show Powered Off before copying the VM or disk.

Your desktop""")
print({"xfce": "Use the applications menu or Alt+F2. Thunar manages your files.",
       "gnome": "Press Super for Activities and type the name of an application. Open Files to browse your home.",
       "plasma": "Open the application launcher or press Alt+Space. Dolphin manages files and Konsole is the terminal.",
       "cwm": "Super+Enter opens xterm, Super+P runs dmenu, and Super+F1 opens the keyboard guide.\nSuper+E opens PCManFM-Qt, Super+M opens Midnight Commander, and Super+L locks the screen.\nPrint Screen saves to ~/Pictures/Screenshots. Super+Shift+Q logs out."}[edition])
repo = ("OpenBSD8" if system == "OpenBSD" else "FreeBSD15") + "-VM-for-VirtualBox"
print(f"""
Checksums
The release's SHA256SUMS-downloads.txt identifies every compressed part.
The SHA256SUMS inside the archive identifies the extracted VDI before boot.
Linux: sha256sum -c SHA256SUMS   BSD: sha256 filename
macOS: shasum -a 256 filename    PowerShell: Get-FileHash filename -Algorithm SHA256

Full documentation, release evidence, and source
https://github.com/AlfredoLlaquet/{repo}
""")
