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
# Some vendor setups exit explicitly, so set the backdrop before their exit.
xsetroot=$(command -v xsetroot)
awk -v cmd="$xsetroot -solid '#252927'" '/^exit([[:space:]]|$)/ && !done {print cmd;done=1} {print} END {if(!done)print cmd}' \
    "$dir/Xsetup_0" > /tmp/mvm-xsetup
cat /tmp/mvm-xsetup > "$dir/Xsetup_0"
rm /tmp/mvm-xsetup
