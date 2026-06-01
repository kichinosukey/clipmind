#!/usr/bin/env bash
# Remove ClipMind ~/.local/bin wrappers and optionally the clone directory.

set -euo pipefail

CLIPMIND_HOME="${CLIPMIND_HOME:-$HOME/.local/share/clipmind}"
BIN_DIR="${CLIPMIND_INSTALL_DIR:-$HOME/.local/bin}"

remove_wrapper() {
  local name="$1"
  local path="${BIN_DIR}/${name}"
  if [[ -f "$path" ]]; then
    rm -f "$path"
    echo "Removed ${path}"
  fi
}

main() {
  remove_wrapper clipmind-run
  remove_wrapper clipmind-repair

  if [[ "${CLIPMIND_REMOVE_REPO:-0}" == "1" ]]; then
    if [[ -d "$CLIPMIND_HOME" ]]; then
      echo "Removing repository: $CLIPMIND_HOME"
      rm -rf "$CLIPMIND_HOME"
    fi
  else
    echo "Repository kept at: $CLIPMIND_HOME"
    echo "To remove it: CLIPMIND_REMOVE_REPO=1 bash uninstall.sh"
  fi

  echo "Chrome Native Messaging manifest and Alfred workflows were not removed."
  echo "Delete manually if needed:"
  echo "  ~/Library/Application Support/Google/Chrome/NativeMessagingHosts/com.clipmind.host.json"
}

main "$@"
