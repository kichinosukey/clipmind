#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="${0:A:h}"
LOCAL_BIN="${HOME}/.local/bin"

resolve_repo_root() {
  if command -v git >/dev/null 2>&1; then
    local root
    root="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null)" || true
    if [[ -n "${root:-}" ]]; then
      print -r -- "$root"
      return 0
    fi
  fi
  print -r -- "${SCRIPT_DIR:h}"
}

write_wrapper() {
  local name="$1"
  local launcher="$2"
  local dest="${LOCAL_BIN}/${name}"
  cat >"$dest" <<EOF
#!/bin/zsh
set -euo pipefail
CLIPMIND_HOME=${(q)CLIPMIND_HOME}
RUNNER="\${CLIPMIND_HOME}/${launcher}"
if [[ ! -x "\$RUNNER" ]]; then
  echo "ClipMind launcher not found: \$RUNNER" >&2
  echo "Re-run: \${CLIPMIND_HOME}/scripts/install-local.sh  (or: \${CLIPMIND_HOME}/install.sh)" >&2
  exit 1
fi
exec "\$RUNNER" "\$@"
EOF
  chmod +x "$dest"
}

CLIPMIND_HOME="$(resolve_repo_root)"

if [[ ! -x "${CLIPMIND_HOME}/clipmind-run" ]]; then
  echo "clipmind-run not found under: ${CLIPMIND_HOME}" >&2
  exit 1
fi

mkdir -p "$LOCAL_BIN"
write_wrapper clipmind-run clipmind-run
write_wrapper clipmind-repair clipmind-repair

case ":${PATH}:" in
  *":${LOCAL_BIN}:"*) ;;
  *)
    echo "Note: ${LOCAL_BIN} is not on PATH." >&2
    echo 'Add: export PATH="${HOME}/.local/bin:$PATH"' >&2
    ;;
esac

echo "Installed clipmind-run and clipmind-repair to ${LOCAL_BIN}"
echo "CLIPMIND_HOME=${CLIPMIND_HOME}"
echo "Next: load chrome-extension/, then: clipmind-repair <extension-id>"
