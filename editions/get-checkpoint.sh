#!/usr/bin/env bash
set -euo pipefail
name="packages-$EDITION"
id=${SOURCE_RUN:-}
if [[ -z $id ]]; then
  # A single-edition preparation may be newer than the last four-edition run.
  # Select the newest available checkpoint for this edition on main.
  runs=$(gh run list --workflow prepare.yml --branch main --limit 100 --json databaseId,status)
  id=$(gh api --method GET "repos/$GITHUB_REPOSITORY/actions/artifacts" -f name="$name" -F per_page=100 |
    jq -r --arg name "$name" --argjson runs "$runs" '
      [.artifacts[] | select(.name == $name and .expired == false)
       | .workflow_run.id as $id | select(any($runs[]; .databaseId == $id))]
      | max_by(.created_at) | .workflow_run.id // empty')
  if [[ -z $id ]]; then
    id=$(jq -r '[.[] | select(.status != "completed")][0].databaseId // empty' <<< "$runs")
  fi
  if [[ -z $id ]]; then
    echo "Run Prepare desktop packages for $EDITION, then supply its run ID." >&2
    exit 1
  fi
fi
[[ $id =~ ^[0-9]+$ ]]
echo "Reading the $EDITION checkpoint from preparation run $id"
echo "PREPARE_RUN=$id" >> "$GITHUB_ENV"
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
