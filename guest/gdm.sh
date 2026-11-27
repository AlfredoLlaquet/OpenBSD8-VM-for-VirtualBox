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
# A preinstalled desktop opens straight into the workspace. The Tour remains
# available in Activities whenever the desktop account chooses to launch it.
version=$(gnome-shell --version | awk '{print $NF}')
case "$version" in [0-9]*) ;; *) exit 1 ;; esac
schemas=/usr/local/share/glib-2.0/schemas
printf "[org.gnome.shell]\nwelcome-dialog-last-shown-version='%s'\n" "$version" > "$schemas/95-mvm-gnome.gschema.override"
glib-compile-schemas "$schemas"
installed=$(GSETTINGS_BACKEND=memory gsettings get org.gnome.shell welcome-dialog-last-shown-version)
printf 'Configured GNOME tour default %s for Shell %s.\n' "$installed" "$version"
[ "$installed" = "'$version'" ]
