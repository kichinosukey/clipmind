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
