#!/usr/bin/env bash
set -euo pipefail
dir=${RUNNER_TEMP:?}/bundle
release="$RUNNER_TEMP/release"
proof="$RUNNER_TEMP/evidence"
mkdir -p "$release"
name=$(basename "$DISK" .vdi)
cd "$dir"
sha256sum -c SHA256SUMS
cp "$GITHUB_WORKSPACE/LICENSE" "$GITHUB_WORKSPACE/THIRD-PARTY-NOTICES.txt" .
cp "$proof/PACKAGES.txt" "$proof/verification.txt" "$release/"
cp "$proof/desktop.png" "$proof/before-login.png" "$release/"
cp "$proof/terminal.png" "$release/"
if [[ -f "$RUNNER_TEMP/lower-memory/verification.txt" ]]; then
  cp "$RUNNER_TEMP/lower-memory/verification.txt" "$release/4096-MiB.txt"
fi
python3 "$GITHUB_WORKSPACE/editions/instructions.py" "$SYSTEM" "$EDITION" "$MEMORY" "$name" > START-HERE.txt
cp START-HERE.txt "$release/"
{
  echo "$name"
  echo "VirtualBox release target: 7.2.22 amd64"
  echo "Verification hypervisor: $BACKEND"
  echo "Full desktop test RAM: $MEMORY MiB; CPUs: 2"
  echo "Source commit: $GITHUB_SHA"
  echo "Package preparation run: https://github.com/$GITHUB_REPOSITORY/actions/runs/$PREPARE_RUN"
  echo "Desktop verification run: https://github.com/$GITHUB_REPOSITORY/actions/runs/$GITHUB_RUN_ID"
  qemu-img info "$name.vdi"
  stat -c 'Extracted VDI file bytes: %s' "$name.vdi"
  cat SHA256SUMS
} > "$release/IMAGE-INFO.txt"
cp "$release/IMAGE-INFO.txt" .
7z a -bd -t7z -mx=3 -mmt=2 -v1800m "$release/$name.7z" "$name.vdi" SHA256SUMS START-HERE.txt LICENSE THIRD-PARTY-NOTICES.txt IMAGE-INFO.txt
7z t -bd "$release/$name.7z.001"
expected=$(cut -d' ' -f1 SHA256SUMS)
actual=$(7z x -so "$release/$name.7z.001" "$name.vdi" | sha256sum | cut -d' ' -f1)
[[ $expected == "$actual" ]]
cd "$release"
sha256sum "$name".7z.* > SHA256SUMS-downloads.txt
sha256sum -c SHA256SUMS-downloads.txt
printf 'Verified archive sizes in bytes:\n' >> IMAGE-INFO.txt
stat -c '%s %n' "$name".7z.* >> IMAGE-INFO.txt
