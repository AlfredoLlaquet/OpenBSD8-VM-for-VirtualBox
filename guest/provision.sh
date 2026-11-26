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

# rc starts the native kernel relinker in the background on every boot.
# Wait before halt can terminate it halfway through the next boot's kernel.
set +x
kernel=$(sysctl -n kern.osversion)
relink_log="/usr/share/relink/kernel/${kernel%%#*}/relink.log"

relink_running() {
    if [ "$#" -gt 0 ]; then
        kill -0 "$1" 2>/dev/null
    else
        pgrep -U 0 -qxf '/bin/ksh .*reorder_kernel$'
    fi
}

wait_for_relink() {
    count=0
    while relink_running "$@"; do
        if [ "$count" -ge 180 ]; then
            echo "OpenBSD kernel relinking exceeded 15 minutes." >&2
            return 1
        fi
        count=$((count + 1))
        sleep 5
    done
    return 0
}

relink_completed() {
    test -f "$relink_log" &&
        grep -Fq 'Kernel has been relinked and is active on next reboot.' "$relink_log" &&
        sha256 -C /var/db/kernel.SHA256 /bsd >/dev/null 2>&1
}

show_relink_failure() {
    echo "Kernel relink diagnostic from $relink_log:" >&2
    if [ -r "$relink_log" ]; then
        tail -n 12 "$relink_log" | cut -c1-320 >&2
    else
        echo "The OpenBSD kernel relinker did not create its log." >&2
    fi
}

echo "Waiting for OpenBSD's kernel relink and verifying the next boot's kernel."
if ! wait_for_relink; then
    show_relink_failure
    exit 1
fi
if ! relink_completed; then
    show_relink_failure
    echo "Retrying the native kernel relink once." >&2
    /usr/libexec/reorder_kernel &
    relink_pid=$!
    if ! wait_for_relink "$relink_pid" || ! wait "$relink_pid" || ! relink_completed; then
        show_relink_failure
        exit 1
    fi
fi
echo "Kernel relink finished; /bsd matches OpenBSD's recorded checksum."
sync
echo "Xfce login, networking, and SSH configuration are ready for the graphical boot test."
