#!/bin/sh
# Runs as root from the installed system on its first boot.
set -eu

echo "Installing the Xfce desktop from OpenBSD's signed package repository"
printf '%s\n' 'https://cdn.openbsd.org/pub/OpenBSD' > /etc/installurl
for attempt in 1 2 3; do
    if pkg_add -I xfce dbus; then
        break
    fi
    if [ "$attempt" -eq 3 ]; then
        exit 1
    fi
    sleep 15
done

test -x /usr/X11R6/bin/Xorg
test -x /usr/local/bin/startxfce4
test -x /usr/local/bin/xfce4-session
id -Gn desktop | tr ' ' '\n' | grep -qx wheel

cat > /home/desktop/.xsession <<'END_SESSION'
#!/bin/sh
exec /usr/local/bin/startxfce4
END_SESSION
chown desktop:desktop /home/desktop/.xsession
chmod 700 /home/desktop/.xsession
rcctl enable messagebus
rcctl enable xenodm
rcctl enable sshd
/usr/sbin/sshd -T | grep -qx 'permitrootlogin no'

# Switch the installer serial console back to the graphical VM console.
# The boot loader also takes this default when no boot.conf file is present.
printf '%s\n' 'set tty pc0' > /etc/boot.conf

# Use the interface name, so VirtualBox can assign a fresh MAC on import.
printf '%s\n' 'inet autoconf' > /etc/hostname.em0
rm -f /var/db/dhcpleased/em0 /etc/ssh/ssh_host_*_key /etc/ssh/ssh_host_*_key.pub
rm -f /tmp/obsd-provision.sh
sync
