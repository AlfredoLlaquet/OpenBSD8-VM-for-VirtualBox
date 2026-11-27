#!/usr/bin/env bash
set -euo pipefail
umask 077

output_dir=${1:?Specify an output directory for the disk archive}
mkdir -p "$output_dir"
output_dir=$(cd "$output_dir" && pwd)
project_dir=$(cd "$(dirname "$0")" && pwd)
work_dir=$(mktemp -d "${RUNNER_TEMP:-${TMPDIR:-/tmp}}/obsd.XXXXXXXX")
trap 'rm -rf -- "$work_dir"' EXIT

checkpoint_dir=${2:-$work_dir/checkpoint}
mkdir -p "$checkpoint_dir"
checkpoint_dir=$(cd "$checkpoint_dir" && pwd)
checkpoint_disk="$checkpoint_dir/packages.qcow2"

disk_name=OpenBSD-8.0-Xfce-amd64
instructions_name=OpenBSD8-VM-for-VirtualBox-INSTRUCTIONS.txt
bundle_dir="$work_dir/bundle"
mkdir -p "$bundle_dir" "$output_dir/evidence"
# These are intentional public first-login credentials, documented in the README.
# build_guest.py still creates a newly salted bcrypt hash for each account.
desktop_password=OpenSesame
root_password=CheckOut_TheCrumbs.org
if [[ -s "$checkpoint_disk" ]]; then
  if [[ ! -r "$checkpoint_dir/desktop-password" || ! -r "$checkpoint_dir/root-password" ]] ||
     ! IFS= read -r checkpoint_desktop_password < "$checkpoint_dir/desktop-password" ||
     ! IFS= read -r checkpoint_root_password < "$checkpoint_dir/root-password"; then
    printf 'The checkpoint login files are missing or incomplete.\n' >&2
    exit 1
  fi
  if [[ $checkpoint_desktop_password != "$desktop_password" ||
        $checkpoint_root_password != "$root_password" ]]; then
    printf 'This checkpoint uses older login credentials. Use a new checkpoint directory for a public build.\n' >&2
    exit 1
  fi
  unset checkpoint_desktop_password checkpoint_root_password
else
  printf '%s\n' "$desktop_password" > "$checkpoint_dir/desktop-password"
  printf '%s\n' "$root_password" > "$checkpoint_dir/root-password"
fi
if [[ ! -s "$project_dir/$instructions_name" ]]; then
  printf 'The public installation instructions are missing: %s\n' "$instructions_name" >&2
  exit 1
fi
export DESKTOP_PASSWORD="$desktop_password" ROOT_PASSWORD="$root_password"

cd "$project_dir"
/usr/bin/python3 -u build_guest.py --output "$bundle_dir/$disk_name.vdi" --output-format vdi \
  --work-dir "$work_dir/guest" --checkpoint "$checkpoint_disk" --disk-size 16G --memory 3072
(cd "$bundle_dir" && sha256sum "$disk_name.vdi" > SHA256SUMS)

/usr/bin/python3 -u verify_desktop.py --disk "$bundle_dir/$disk_name.vdi" --evidence "$output_dir/evidence"
(cd "$bundle_dir" && sha256sum --check SHA256SUMS)

cp "$instructions_name" "$bundle_dir/$instructions_name"
cp LICENSE THIRD-PARTY-NOTICES.txt "$bundle_dir/"
unset DESKTOP_PASSWORD ROOT_PASSWORD desktop_password root_password

printf '\nPackaging the verified VDI and complete installation instructions.\n'
(cd "$bundle_dir" && zip -q -6 "$work_dir/$disk_name.zip" "$disk_name.vdi" "$instructions_name" LICENSE THIRD-PARTY-NOTICES.txt SHA256SUMS)
unzip -tq "$work_dir/$disk_name.zip"
mv "$work_dir/$disk_name.zip" "$output_dir/$disk_name.zip"
cp "$bundle_dir/$instructions_name" "$output_dir/$instructions_name"
(cd "$output_dir" && sha256sum "$disk_name.zip" > "$disk_name.zip.sha256")
du -h "$output_dir/$disk_name.zip"
