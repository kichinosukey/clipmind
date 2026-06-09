"""Tests for shared path helpers."""

import os
import subprocess
import sys


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
    CLIPMIND_SUPPORT_DIR,
    CONFIG_PATH,
    CONFIG_SUPPORT_DIR,
    JOBS_DIR,
    KEYCHAIN_SERVICE,
    STATUS_DIR,
)
from pathlib import Path

config_hub = Path.home() / "Library" / "Application Support" / "ConfigHub"
clipmind = Path.home() / "Library" / "Application Support" / "ClipMind"
assert CONFIG_SUPPORT_DIR == config_hub
assert CONFIG_PATH == config_hub / "config.json"
assert CLIPMIND_SUPPORT_DIR == clipmind
assert JOBS_DIR == clipmind / "jobs"
assert STATUS_DIR == JOBS_DIR
assert KEYCHAIN_SERVICE == "com.kichinosukey.confighub"
""",
        ],
        capture_output=True,
        env=env,
        text=True,
    )

    assert result.returncode == 0, result.stderr
