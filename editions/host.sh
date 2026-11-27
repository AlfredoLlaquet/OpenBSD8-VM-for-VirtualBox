#!/usr/bin/env bash
set -euo pipefail
if [[ ${RUNNER_ENVIRONMENT:-} == github-hosted ]]; then
  for toolchain in /usr/local/lib/android/sdk /usr/share/dotnet /usr/local/.ghcup /opt/ghc; do
    if (( $(df -Pk "$RUNNER_TEMP" | awk 'END {print $4}') >= 45 * 1024 * 1024 )); then break; fi
    sudo rm -rf -- "$toolchain"
  done
fi
apt_sources=(-o Acquire::Retries=3)
if [[ -f /etc/apt/sources.list.d/ubuntu.sources ]]; then
  # The image only needs Ubuntu packages. Unrelated hosted-runner feeds can
  # be unavailable even while the signed Ubuntu archives are healthy.
  apt_sources+=(-o Dir::Etc::sourcelist=/etc/apt/sources.list.d/ubuntu.sources -o Dir::Etc::sourceparts=-)
fi
sudo apt-get "${apt_sources[@]}" -qq update
sudo apt-get "${apt_sources[@]}" install -y --no-install-recommends qemu-system-x86 qemu-utils seabios openssh-client signify-openbsd python3-pexpect python3-bcrypt python3-pil genisoimage p7zip-full tesseract-ocr tesseract-ocr-eng
if [[ -c /dev/kvm && ! -w /dev/kvm ]]; then
  sudo setfacl -m "u:$(id -un):rw" /dev/kvm
fi
df -h "${RUNNER_TEMP:-.}"
