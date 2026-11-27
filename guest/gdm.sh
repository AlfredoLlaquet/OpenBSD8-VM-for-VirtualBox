#!/bin/sh
set -eu
# OpenBSD builds GDM with the _gdm account and a matching dconf profile.
# Put the local database above the packaged greeter defaults in that profile.
etc=/etc
profile=_gdm
if [ "$(uname -s)" = FreeBSD ]; then etc=/usr/local/etc; profile=gdm; fi
mkdir -p "$etc/dconf/profile" "$etc/dconf/db/gdm.d" /home/desktop/.config
printf '%s\n' user-db:user system-db:gdm file-db:/usr/local/share/gdm/greeter-dconf-defaults > "$etc/dconf/profile/$profile"
printf '[org/gnome/login-screen]\ndisable-user-list=true\n' > "$etc/dconf/db/gdm.d/00-login"
dconf update "$etc/dconf/db"
[ "$(DCONF_PROFILE="$profile" dconf read /org/gnome/login-screen/disable-user-list)" = true ]
printf 'yes\n' > /home/desktop/.config/gnome-initial-setup-done
