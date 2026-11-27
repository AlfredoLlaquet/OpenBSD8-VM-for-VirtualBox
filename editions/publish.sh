#!/usr/bin/env bash
set -euo pipefail
export GH_REPO="$GITHUB_REPOSITORY"
cd "$RUNNER_TEMP/release"
name=$(basename "$DISK" .vdi)
tag="${SYSTEM,,}-$VERSION-$EDITION-$GITHUB_RUN_ID-$GITHUB_RUN_ATTEMPT"
parts=("$name".7z.*)
notes="$RUNNER_TEMP/release-notes.md"
{
  echo "A standalone $SYSTEM $VERSION virtual disk with $LABEL installed."
  echo
  echo "Download all ${#parts[@]} numbered archive part(s) into one folder and extract \`$name.7z.001\` once with 7-Zip. Open \`START-HERE.txt\` for the VirtualBox settings and initial login."
  echo
  echo "The attached verification report records the graphical login, terminal, network, and reboot tests. The inventory and screenshots come from this disk."
  echo
  echo "[Installation guide](https://github.com/$GITHUB_REPOSITORY#readme) · [Verification run](https://github.com/$GITHUB_REPOSITORY/actions/runs/$GITHUB_RUN_ID)"
} > "$notes"
gh release create "$tag" --draft --target "$GITHUB_SHA" --title "$SYSTEM $VERSION with $LABEL for VirtualBox" --notes-file "$notes" ./*
rid=$(gh api "repos/$GITHUB_REPOSITORY/releases?per_page=100" | jq -er --arg tag "$tag" '.[] | select(.tag_name==$tag and .draft) | .id')
gh api --paginate "repos/$GITHUB_REPOSITORY/releases/$rid/assets" --jq '.[] | [.name,.size,.digest] | @tsv' > "$RUNNER_TEMP/assets.tsv"
python3 - "$RUNNER_TEMP/assets.tsv" <<'PY'
import hashlib
from pathlib import Path
import sys
entries = {}
for row in Path(sys.argv[1]).read_text().splitlines():
    name, size, digest = row.split("\t")
    entries[name] = (int(size), digest)
for path in Path.cwd().iterdir():
    with path.open("rb") as stream:
        digest = "sha256:" + hashlib.file_digest(stream, "sha256").hexdigest()
    if entries.get(path.name) != (path.stat().st_size, digest):
        raise SystemExit(f"GitHub asset checksum or size mismatch: {path.name}")
PY
latest=false
if [[ $SYSTEM == FreeBSD && $EDITION == xfce ]]; then latest=true; fi
gh release edit "$tag" --draft=false --latest="$latest"
gh release view "$tag" --json url,isDraft,assets --jq '{url,isDraft,assets:[.assets[].name]}'
