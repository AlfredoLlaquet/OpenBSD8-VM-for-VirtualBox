#!/bin/sh
set -eu
cd "$(dirname "$0")"
dest=/home/desktop
share=/usr/local/share/mvm
install -d "$share" /usr/local/bin "$dest/Pictures/Screenshots"
cp -R home/. "$dest/"
for file in bin/*; do install -m 755 "$file" "/usr/local/bin/${file##*/}"; done
install -m 644 KEYS.txt "$share/KEYS.txt"
# A diagonal gold seam over charcoal. PPM is portable and feh scales it at login.
awk 'BEGIN {w=640; h=360; print "P3",w,h,255; for(y=0;y<h;y++)for(x=0;x<w;x++){
  d=x-2*y+144; if(d==0 || d==1) print 142,125,89;
  else if(d>=-9 && d<0) print 47,54,47;
  else if(d>=2 && d<=9) print 37,44,39;
  else if(d>=0) print 32,36,35; else print 29,33,32;
}}' > "$share/wallpaper.ppm"
printf '%s\n' '#!/bin/sh' 'exec /usr/local/bin/mvm-cwm-session' > "$dest/.xsession"
chmod 700 "$dest/.xsession"
chown -R "desktop:$(id -gn desktop)" "$dest"
