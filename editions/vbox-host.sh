#!/usr/bin/env bash
# Install the pinned Oracle base package on a disposable Ubuntu 24.04 build host.
set -euo pipefail
pkg=virtualbox-7.2_7.2.22-175245~Ubuntu~noble_amd64.deb
cd "${RUNNER_TEMP:?}"
curl -fsSL --retry 3 --proto '=https' --proto-redir '=https' \
  "https://download.virtualbox.org/virtualbox/7.2.22/$pkg" -o "$pkg"
echo "426f192dc4515cd02a687a39408c0b6b0d7741de77ff7c345efd92e6090c96ee  $pkg" | sha256sum -c -
sudo apt-get install -y --no-install-recommends build-essential "linux-headers-$(uname -r)" "./$pkg"
if [[ ! -c /dev/vboxdrv ]]; then sudo /sbin/vboxconfig; fi
# Release hardware virtualization after QEMU exits on this dedicated hosted VM.
for module in kvm_intel kvm_amd; do
  if [[ -d /sys/module/$module ]]; then sudo modprobe -r "$module"; fi
done
sudo modprobe vboxdrv
for device in /dev/vboxdrv /dev/vboxdrvu; do
  if [[ -c $device ]]; then sudo setfacl -m "u:$(id -un):rw" "$device"; fi
done
VBoxManage --version | grep -E '^7\.2\.22r'
