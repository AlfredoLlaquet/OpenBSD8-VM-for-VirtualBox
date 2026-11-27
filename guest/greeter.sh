#!/bin/sh
set -eu
dir=$1
cat >> "$dir/Xresources" <<'RES'
! cwm graphical login
xlogin*greeting: cwm  /  CLIENTHOST
xlogin*background: #282d2b
xlogin*foreground: #cfd6cb
xlogin*greetColor: #ceb483
xlogin*promptColor: #a4c2aa
xlogin*failColor: #db9287
xlogin*borderWidth: 1
xlogin*frameWidth: 1
RES
# The dedicated cwm greeter needs only a background. The vendor Xsetup also
# opens a console window which would otherwise follow the user into cwm.
xsetroot=$(command -v xsetroot)
printf '%s\n' '#!/bin/sh' "exec $xsetroot -solid '#252927'" > "$dir/Xsetup_0"
chmod 755 "$dir/Xsetup_0"
