#!/bin/sh
# Runs as root once the OpenBSD X sets and the desktop packages are installed.
set -eux
PATH=/bin:/usr/bin:/sbin:/usr/sbin:/usr/X11R6/bin:/usr/local/bin:/usr/local/sbin
export PATH

if ! launcher=$(command -v startxfce4); then
    echo "The installed packages did not provide the Xfce session launcher." >&2
    pkg_info -aI | grep -i xfce >&2 || :
    exit 1
fi
id desktop
primary_group=$(id -gn desktop)
case " $(id -Gn desktop) " in
    *" wheel "*) ;;
    *) usermod -G wheel desktop ;;
esac

if command -v ck-launch-session >/dev/null; then
    printf '#!/bin/sh\nexec "%s" --with-ck-launch\n' "$launcher" > /home/desktop/.xsession
else
    echo "ConsoleKit is unavailable; configuring the standard Xfce session." >&2
    printf '#!/bin/sh\nexec "%s"\n' "$launcher" > /home/desktop/.xsession
fi
chown "desktop:$primary_group" /home/desktop/.xsession
chmod 700 /home/desktop/.xsession
rcctl enable messagebus
rcctl enable xenodm
rcctl enable sshd
if ! /usr/sbin/sshd -T | grep -qx 'permitrootlogin no'; then
    { printf '%s\n' 'PermitRootLogin no'; cat /etc/ssh/sshd_config; } > /etc/ssh/sshd_config.obsd
    /usr/sbin/sshd -t -f /etc/ssh/sshd_config.obsd
    mv /etc/ssh/sshd_config.obsd /etc/ssh/sshd_config
fi
/usr/sbin/sshd -t

# Switch the installer serial console back to the graphical VM console.
# The boot loader also takes this default when no boot.conf file is present.
printf '%s\n' 'set tty pc0' > /etc/boot.conf
sed '/^tty00[[:space:]]/s/[[:space:]]on[[:space:]]/ off /' /etc/ttys > /tmp/obsd-ttys
cat /tmp/obsd-ttys > /etc/ttys
rm /tmp/obsd-ttys

# Use the interface name, so VirtualBox can assign a fresh MAC on import.
printf '%s\n' 'inet autoconf' > /etc/hostname.em0
rm -f /var/db/dhcpleased/em0 /etc/ssh/ssh_host_*_key /etc/ssh/ssh_host_*_key.pub
sync
echo "Xfce login, networking, and SSH configuration are ready for the graphical boot test."
