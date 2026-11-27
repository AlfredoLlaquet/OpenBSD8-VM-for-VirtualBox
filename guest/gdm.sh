#!/bin/sh
set -eu
# Both BSD packages read the local dconf profile below. Make authentication use
# an explicit name field for predictable first login on a freshly copied disk.
etc=/etc
[ "$(uname -s)" != FreeBSD ] || etc=/usr/local/etc
mkdir -p "$etc/dconf/profile" "$etc/dconf/db/gdm.d" /home/desktop/.config
if [ ! -f "$etc/dconf/profile/gdm" ]; then
    printf '%s\n' user-db:user system-db:gdm file-db:/usr/local/share/gdm/greeter-dconf-defaults > "$etc/dconf/profile/gdm"
elif ! grep -qx 'system-db:gdm' "$etc/dconf/profile/gdm"; then
    printf '%s\n' system-db:gdm >> "$etc/dconf/profile/gdm"
fi
printf '[org/gnome/login-screen]\ndisable-user-list=true\n' > "$etc/dconf/db/gdm.d/00-login"
dconf update
printf 'yes\n' > /home/desktop/.config/gnome-initial-setup-done
