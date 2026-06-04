"""Tests for shared path and environment helpers."""

import os
import subprocess
import sys

from clipmind.paths import load_project_dotenv


def test_shared_runtime_paths_use_application_support(tmp_path):
    home = tmp_path / "home"
    env = os.environ.copy()
    env["HOME"] = str(home)

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            """
from clipmind.paths import (
    APPLICATION_SUPPORT_DIR,
    CONFIG_PATH,
    JOBS_DIR,
    KEYCHAIN_SERVICE,
    STATUS_DIR,
)
from pathlib import Path

expected = Path.home() / "Library" / "Application Support" / "ClipMind"
assert APPLICATION_SUPPORT_DIR == expected
assert CONFIG_PATH == expected / "config.json"
assert JOBS_DIR == expected / "jobs"
assert STATUS_DIR == JOBS_DIR
assert KEYCHAIN_SERVICE == "com.kichinosukey.clipmind"
""",
        ],
        capture_output=True,
        env=env,
        text=True,
    )

    assert result.returncode == 0, result.stderr


class TestLoadProjectDotenv:
    def test_load_project_dotenv_respects_explicit_path_from_any_cwd(self, tmp_path, monkeypatch):
        """Explicit dotenv path is loaded even when cwd is elsewhere."""
        env_path = tmp_path / ".env"
        env_path.write_text("CLIPMIND_SENTINEL=loaded-from-file\n", encoding="utf-8")

        other_dir = tmp_path / "elsewhere"
        other_dir.mkdir()
        monkeypatch.chdir(other_dir)
        monkeypatch.delenv("CLIPMIND_SENTINEL", raising=False)

        load_project_dotenv(env_path=env_path, override=True)

        assert os.getenv("CLIPMIND_SENTINEL") == "loaded-from-file"
