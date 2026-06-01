#!/bin/zsh
set -euo pipefail

LOCAL_BIN="${HOME}/.local/bin"
removed=0

for name in clipmind-run clipmind-repair; do
  path="${LOCAL_BIN}/${name}"
  if [[ -f "$path" ]]; then
    rm -f "$path"
    removed=1
    echo "Removed ${path}"
  fi
done

if [[ $removed -eq 0 ]]; then
  echo "No ClipMind wrappers found in ${LOCAL_BIN}"
fi
