#!/bin/sh
set -eu
export PATH=/bin:/usr/bin:/sbin:/usr/sbin:/usr/X11R6/bin:/usr/local/bin:/usr/local/sbin
case "$MVM_EDITION" in
  gnome)
    rcctl disable xenodm
    rcctl enable messagebus multicast avahi_daemon gdm
    rcctl order messagebus
    config=/etc/gdm/custom.conf
    sed -i '/^\[daemon\]$/a\
WaylandEnable=false\
InitialSetupEnable=false' "$config"
    sh /tmp/mvm-edition/gdm.sh
    ;;
  plasma)
    # Older package checkpoints can contain the unrelated Dolphin emulator.
    if pkg_info -e dolphin >/dev/null 2>&1; then pkg_delete -I dolphin; fi
    if ! pkg_info -e kf6-dolphin >/dev/null 2>&1; then pkg_add -I kf6-dolphin; fi
    usermod -L kde desktop
    usermod -G wheel,_shutdown desktop
    printf '%s\n' 'kern.maxfiles=65535' >> /etc/sysctl.conf
    rcctl enable messagebus xenodm
    # Keep the greeter background, then hand Plasma a clean desktop.
    sed -i '/^[^#].*\/xconsole[[:space:]]/s/^/# /' /etc/X11/xenodm/Xsetup_0
    cat > /home/desktop/.xsession <<'SESSION'
#!/bin/sh
XDG_RUNTIME_DIR=$(mktemp -d "/tmp/plasma-$(id -u).XXXXXXXX") || exit 1
export XDG_RUNTIME_DIR LIBGL_ALWAYS_SOFTWARE=1 LANG=en_US.UTF-8
trap 'rm -rf "$XDG_RUNTIME_DIR"' EXIT
/usr/local/bin/ck-launch-session /usr/local/bin/dbus-run-session -- /usr/local/bin/startplasma-x11
SESSION
    mkdir -p /home/desktop/.config
    printf '[KSplash]\nEngine=none\nTheme=None\n' > /home/desktop/.config/ksplashrc
    printf '[Compositing]\nEnabled=false\n' > /home/desktop/.config/kwinrc
    ;;
  cwm)
    sh /tmp/mvm-edition/cwm/install.sh
    sh /tmp/mvm-edition/greeter.sh /etc/X11/xenodm
    rcctl enable messagebus xenodm
    ;;
  *) exit 1 ;;
esac
if [ -e /home/desktop/.xsession ]; then chmod 700 /home/desktop/.xsession; fi
chown -R "desktop:$(id -gn desktop)" /home/desktop
pkg_info -q | sort > /var/db/mvm-packages
