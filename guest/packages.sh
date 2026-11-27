#!/bin/sh
# This is the last stage included in the reusable, powered-off checkpoint.
set -eux
if [ "$(uname -r)" != "8.0" ]; then
    echo "This package checkpoint requires an installed OpenBSD 8.0 guest." >&2
    exit 1
fi

# OpenBSD starts KARL in the background at boot. syspatch refuses to run
# concurrently with it, including when it only needs to check for updates.
set +x
waits=0
while pgrep -U 0 -qxf '/bin/ksh .*reorder_kernel$'; do
    if [ "$waits" -eq 0 ]; then
        echo "Waiting for OpenBSD's first-boot kernel relink before applying patches."
    elif [ "$waits" -ge 180 ]; then
        echo "Kernel relinking did not finish within 15 minutes; cannot safely apply patches." >&2
        exit 1
    fi
    waits=$((waits + 1))
    sleep 5
done
set -x

for mirror in https://cdn.openbsd.org/pub/OpenBSD https://ftp.openbsd.org/pub/OpenBSD; do
    printf '%s\n' "$mirror" > /etc/installurl
    if syspatch; then
        patch_status=0
    else
        patch_status=$?
    fi
    case "$patch_status" in
        0) echo "Applied the available signed OpenBSD 8.0 system patches."; break ;;
        2) echo "No additional OpenBSD 8.0 system patches were available."; break ;;
        *) echo "OpenBSD 8.0 syspatch failed against $mirror (status $patch_status)." >&2 ;;
    esac
done
case "$patch_status" in
    0) syspatch -l ;;
    2) : ;;
    *) echo "Neither official mirror completed the OpenBSD 8.0 patch check." >&2; exit "$patch_status" ;;
esac
printf '%s\n' 'https://cdn.openbsd.org/pub/OpenBSD' > /etc/installurl
case "${MVM_EDITION:-xfce}" in
    xfce) set -- xfce dbus consolekit2 polkit ;;
    gnome) set -- gnome gdm firefox dbus consolekit2 polkit ;;
    plasma) set -- kde-plasma kwin-x11 kf6-dolphin konsole firefox dbus consolekit2 polkit ;;
    cwm) set -- dmenu tint2 pcmanfm-qt mc picom conky-- feh dunst scrot parcellite \
        lxappearance vim-- geany firefox zathura zathura-pdf-poppler mpv fastfetch \
        jetbrains-mono qt6ct adwaita-qt6 gnome-themes-extra adwaita-icon-theme dbus ;;
    *) echo "Unknown edition: $MVM_EDITION" >&2; exit 1 ;;
esac
for attempt in 1 2 3; do
    if pkg_add -I "$@"; then
        echo "Installed the selected desktop packages."
        exit 0
    else
        result=$?
        echo "Package installation attempt $attempt exited with status $result." >&2
    fi
    if [ "$attempt" -lt 3 ]; then
        sleep 15
    fi
done
exit "$result"
