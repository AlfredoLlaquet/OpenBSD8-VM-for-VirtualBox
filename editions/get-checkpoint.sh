#!/usr/bin/env bash
set -euo pipefail
id=${SOURCE_RUN:-}
if [[ -z $id ]]; then
  id=$(gh run list --workflow prepare.yml --branch main --limit 1 --json databaseId --jq '.[0].databaseId')
fi
[[ $id =~ ^[0-9]+$ ]]
echo "Reading the $EDITION checkpoint from preparation run $id"
echo "PREPARE_RUN=$id" >> "$GITHUB_ENV"
name="packages-$EDITION"
mkdir -p "$RUNNER_TEMP/checkpoint"
for ((attempt=0; attempt<170; attempt++)); do
  if gh api "repos/$GITHUB_REPOSITORY/actions/runs/$id/artifacts" --jq '.artifacts[] | select(.expired == false) | .name' |
      grep -Fxq "$name"; then
    gh run download "$id" --name "$name" --dir "$RUNNER_TEMP/checkpoint"
    (cd "$RUNNER_TEMP/checkpoint" && sha256sum -c SHA256SUMS && qemu-img check -q packages.qcow2)
    exit 0
  fi
  if [[ $(gh run view "$id" --json status --jq '.status') == completed ]]; then
    echo "Preparation run $id finished without a $name checkpoint." >&2
    exit 1
  fi
  sleep 45
done
echo "Timed out waiting for preparation run $id." >&2
exit 1
