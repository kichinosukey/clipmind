"""Shared path and environment helpers for ClipMind."""

from __future__ import annotations

import re
import tempfile
from pathlib import Path

NATIVE_HOST_NAME = "com.clipmind.host"

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = PROJECT_ROOT / ".env"

NATIVE_HOST_DIR = PROJECT_ROOT / "native-host"
NATIVE_HOST_SCRIPT = NATIVE_HOST_DIR / "clipmind_host.py"
NATIVE_RUNNER_SCRIPT = NATIVE_HOST_DIR / "clipmind_runner.py"

VENV_DIR = PROJECT_ROOT / ".venv"
VENV_PYTHON = VENV_DIR / "bin" / "python"

CHROME_NATIVE_HOST_DIR = (
    Path.home()
    / "Library"
    / "Application Support"
    / "Google"
    / "Chrome"
    / "NativeMessagingHosts"
)
CHROME_NATIVE_HOST_MANIFEST = CHROME_NATIVE_HOST_DIR / f"{NATIVE_HOST_NAME}.json"

ALFRED_WORKFLOWS_DIR = (
    Path.home()
    / "Library"
    / "Application Support"
    / "Alfred"
    / "Alfred.alfredpreferences"
    / "workflows"
)

STATUS_DIR = Path(tempfile.gettempdir()) / "clipmind_status"

DEFAULT_OUTROOT = str(PROJECT_ROOT / "data")
DEFAULT_WHISPER_BIN = "whisper-cli"
DEFAULT_WHISPER_MODEL = str(Path.home() / ".local" / "share" / "whisper" / "models" / "ggml-base.en.bin")


def load_project_dotenv(
    env_path: Path | None = None,
    *,
    override: bool = False,
) -> bool:
    """Load the repository .env explicitly so cwd does not matter."""
    from dotenv import load_dotenv

    target_path = Path(env_path) if env_path is not None else ENV_PATH
    return load_dotenv(dotenv_path=target_path, override=override)


def embedded_venv_path_warnings(project_root: Path | None = None) -> list[str]:
    """Report stale absolute paths embedded in virtualenv helper scripts."""
    root = Path(project_root) if project_root is not None else PROJECT_ROOT
    venv_dir = root / ".venv"
    warnings: list[str] = []

    if not (venv_dir / "bin" / "python").exists():
        warnings.append(
            f"Virtualenv Python is missing: {venv_dir / 'bin' / 'python'}"
        )
        return warnings

    expected_venv = str(venv_dir)

    activate_path = venv_dir / "bin" / "activate"
    if activate_path.exists():
        activate_text = activate_path.read_text(encoding="utf-8")
        match = re.search(r"^VIRTUAL_ENV='([^']+)'", activate_text, re.MULTILINE)
        if match and match.group(1) != expected_venv:
            warnings.append(
                "Virtualenv activate script still points at the previous repository path."
            )

    expected_shebang = f"#!{venv_dir / 'bin' / 'python'}"
    for entry_name in ("pytest", "coverage"):
        entry_path = venv_dir / "bin" / entry_name
        if not entry_path.exists():
            continue
        first_line = entry_path.read_text(encoding="utf-8").splitlines()[0]
        if first_line.startswith("#!") and first_line != expected_shebang:
            warnings.append(
                f"Virtualenv entrypoint '{entry_name}' still embeds the previous repository path."
            )

    return warnings
