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
su -l desktop -c "/usr/local/bin/dbus-run-session -- /usr/local/bin/gsettings set org.gnome.shell welcome-dialog-last-shown-version '$version'"
su -l desktop -c '/usr/local/bin/gsettings get org.gnome.shell welcome-dialog-last-shown-version' | grep -Fx "'$version'"
