#!/usr/bin/env bash
# ClipMind bootstrap installer (macOS). Safe to run: curl -fsSL .../install.sh | bash

set -euo pipefail

CLIPMIND_REPO_URL="${CLIPMIND_REPO_URL:-https://github.com/kichinosukey/clipmind.git}"
CLIPMIND_BRANCH="${CLIPMIND_BRANCH:-main}"
CLIPMIND_HOME="${CLIPMIND_HOME:-$HOME/.local/share/clipmind}"
BIN_DIR="${CLIPMIND_INSTALL_DIR:-$HOME/.local/bin}"

unset GIT_DIR GIT_WORK_TREE

die() {
  echo "Error: $*" >&2
  exit 1
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "'$1' is required."
}

path_contains_dir() {
  local dir="$1"
  case ":$PATH:" in
    *":$dir:"*) return 0 ;;
    *) return 1 ;;
  esac
}

detect_profile_file() {
  local shell_name
  shell_name="$(basename "${SHELL:-}")"
  case "$shell_name" in
    zsh)
      printf '%s\n' "${HOME}/.zshrc"
      ;;
    bash)
      if [[ -f "${HOME}/.bashrc" ]]; then
        printf '%s\n' "${HOME}/.bashrc"
      else
        printf '%s\n' "${HOME}/.bash_profile"
      fi
      ;;
    *)
      printf '%s\n' "${HOME}/.profile"
      ;;
  esac
}

append_path_to_profile_if_needed() {
  local profile line
  if path_contains_dir "$BIN_DIR"; then
    return 0
  fi

  profile="$(detect_profile_file)"
  mkdir -p "$(dirname "$profile")"
  touch "$profile"
  line="export PATH=\"$BIN_DIR:\$PATH\""

  if grep -Fqx "$line" "$profile" 2>/dev/null; then
    return 0
  fi

  {
    printf '\n# Added by ClipMind installer\n'
    printf '%s\n' "$line"
  } >>"$profile"

  echo "Updated shell profile: $profile"
}

is_git_repo_root() {
  local resolved_home git_toplevel resolved_toplevel
  [[ -d "$CLIPMIND_HOME" ]] || return 1
  resolved_home="$(cd "$CLIPMIND_HOME" && pwd -P)" || return 1
  git_toplevel="$(git -C "$resolved_home" rev-parse --show-toplevel 2>/dev/null)" || return 1
  resolved_toplevel="$(cd "$git_toplevel" && pwd -P)" || return 1
  [[ "$resolved_home" == "$resolved_toplevel" ]]
}

ensure_clone() {
  local current_branch
  if is_git_repo_root; then
    if [[ "${CLIPMIND_SKIP_GIT_UPDATE:-0}" == "1" ]]; then
      echo "Using existing clone (git update skipped): $CLIPMIND_HOME"
      return 0
    fi
    echo "Updating existing clone: $CLIPMIND_HOME"
    git -C "$CLIPMIND_HOME" fetch origin "$CLIPMIND_BRANCH"
    current_branch="$(git -C "$CLIPMIND_HOME" branch --show-current)"
    if [[ "$current_branch" == "$CLIPMIND_BRANCH" ]]; then
      git -C "$CLIPMIND_HOME" pull --ff-only origin "$CLIPMIND_BRANCH"
    else
      echo "Fetched $CLIPMIND_BRANCH; current branch is ${current_branch:-detached}; update skipped."
    fi
    return 0
  fi

  if [[ -e "$CLIPMIND_HOME" ]]; then
    die "$CLIPMIND_HOME exists but is not a git repository. Remove it or set CLIPMIND_HOME elsewhere."
  fi

  echo "Cloning ClipMind into: $CLIPMIND_HOME"
  mkdir -p "$(dirname "$CLIPMIND_HOME")"
  git clone --branch "$CLIPMIND_BRANCH" --depth 1 "$CLIPMIND_REPO_URL" "$CLIPMIND_HOME"
}

ensure_venv() {
  local venv_python="$CLIPMIND_HOME/.venv/bin/python"
  if [[ ! -x "$venv_python" ]]; then
    echo "Creating virtualenv in $CLIPMIND_HOME/.venv"
    python3 -m venv "$CLIPMIND_HOME/.venv"
    venv_python="$CLIPMIND_HOME/.venv/bin/python"
  fi
  if ! "$venv_python" -m pip --version >/dev/null 2>&1; then
    echo "Bootstrapping pip in virtualenv..."
    "$venv_python" -m ensurepip --upgrade
  fi
}

install_python_deps() {
  local venv_python="$CLIPMIND_HOME/.venv/bin/python"
  echo "Installing Python dependencies..."
  "$venv_python" -m pip install --upgrade pip
  "$venv_python" -m pip install -r "$CLIPMIND_HOME/requirements.txt"
}

warn_brew_deps() {
  if ! command -v brew >/dev/null 2>&1; then
    echo "Note: Homebrew not found. Install yt-dlp and ffmpeg manually when ready." >&2
    return 0
  fi
  for pkg in yt-dlp ffmpeg; do
    if ! brew list "$pkg" >/dev/null 2>&1; then
      echo "Note: brew install $pkg  (recommended before running the pipeline)" >&2
    fi
  done
}

ensure_env_file() {
  if [[ -f "$CLIPMIND_HOME/.env" ]]; then
    return 0
  fi
  if [[ -f "$CLIPMIND_HOME/.env.example" ]]; then
    cp "$CLIPMIND_HOME/.env.example" "$CLIPMIND_HOME/.env"
    echo "Created $CLIPMIND_HOME/.env from .env.example — edit API keys and OUTROOT."
  fi
}

main() {
  require_cmd git
  require_cmd python3

  python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' \
    || die "Python 3.10+ is required."

  ensure_clone
  ensure_venv
  install_python_deps
  ensure_env_file

  if [[ ! -x "$CLIPMIND_HOME/scripts/install-local.sh" ]]; then
    die "scripts/install-local.sh not found in $CLIPMIND_HOME"
  fi
  /bin/zsh "$CLIPMIND_HOME/scripts/install-local.sh"

  append_path_to_profile_if_needed
  warn_brew_deps

  cat <<EOF

ClipMind installed.
  CLIPMIND_HOME=$CLIPMIND_HOME
  Commands:    clipmind-run, clipmind-repair  (in $BIN_DIR)

Next steps:
  1. Edit $CLIPMIND_HOME/.env
  2. Prepare Whisper.cpp (see README)
  3. brew install yt-dlp ffmpeg   (if not already installed)
  4. Load chrome-extension/ in chrome://extensions
  5. clipmind-repair <extension-id>

Open a new shell if 'clipmind-run' is not found yet.
EOF
}

main "$@"
