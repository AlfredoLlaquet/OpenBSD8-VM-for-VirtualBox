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
bundle_dir="$work_dir/bundle"
mkdir -p "$bundle_dir" "$output_dir/evidence"
if [[ -s "$checkpoint_disk" ]]; then
  IFS= read -r desktop_password < "$checkpoint_dir/desktop-password"
  IFS= read -r root_password < "$checkpoint_dir/root-password"
  if [[ ! $desktop_password =~ ^[0-9a-f]{24}$ || ! $root_password =~ ^[0-9a-f]{24}$ ]]; then
    printf 'The checkpoint login files are incomplete.\n' >&2
    exit 1
  fi
else
  desktop_password=$(openssl rand -hex 12)
  root_password=$(openssl rand -hex 12)
  printf '%s\n' "$desktop_password" > "$checkpoint_dir/desktop-password"
  printf '%s\n' "$root_password" > "$checkpoint_dir/root-password"
fi
if [[ ${GITHUB_ACTIONS:-} == true ]]; then
  printf '::add-mask::%s\n' "$desktop_password" "$root_password"
fi
export DESKTOP_PASSWORD="$desktop_password" ROOT_PASSWORD="$root_password"

cd "$project_dir"
/usr/bin/python3 -u build_guest.py --output "$work_dir/installed.qcow2" --work-dir "$work_dir/guest" --checkpoint "$checkpoint_disk" --disk-size 16G --memory 3072

printf '\nConverting the installed disk to VDI and comparing guest-visible sectors.\n'
qemu-img convert -f qcow2 -O vdi "$work_dir/installed.qcow2" "$bundle_dir/$disk_name.vdi"
qemu-img compare -f qcow2 -F vdi "$work_dir/installed.qcow2" "$bundle_dir/$disk_name.vdi"
rm -- "$work_dir/installed.qcow2"
(cd "$bundle_dir" && sha256sum "$disk_name.vdi" > SHA256SUMS)

/usr/bin/python3 -u verify_desktop.py --disk "$bundle_dir/$disk_name.vdi" --evidence "$output_dir/evidence"
(cd "$bundle_dir" && sha256sum --check SHA256SUMS)

cp VirtualBox.txt "$bundle_dir/VirtualBox.txt"
{
  printf 'OpenBSD graphical login\n\nUsername: desktop\nPassword: %s\n' "$desktop_password"
  printf '\nFor system administration, use su - with this root password: %s\n' "$root_password"
  printf '\nYou can change each account password with passwd while signed in as that account.\n'
} > "$bundle_dir/FIRST-LOGIN.txt"
unset DESKTOP_PASSWORD ROOT_PASSWORD desktop_password root_password

printf '\nPackaging the verified VDI and first-login instructions.\n'
(cd "$bundle_dir" && zip -q -6 "$work_dir/$disk_name.zip" "$disk_name.vdi" VirtualBox.txt FIRST-LOGIN.txt SHA256SUMS)
unzip -tq "$work_dir/$disk_name.zip"
mv "$work_dir/$disk_name.zip" "$output_dir/$disk_name.zip"
(cd "$output_dir" && sha256sum "$disk_name.zip" > "$disk_name.zip.sha256")
du -h "$output_dir/$disk_name.zip"
