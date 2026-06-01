"""Tests for the repo launcher scripts."""

import subprocess

from clipmind.paths import PROJECT_ROOT


class TestLauncherScripts:
    def test_clipmind_run_resolves_repo_from_any_cwd(self, tmp_path):
        """Launcher works from outside the repo without activating the virtualenv."""
        launcher = PROJECT_ROOT / "clipmind-run"

        result = subprocess.run(
            ["/bin/zsh", str(launcher)],
            cwd=tmp_path,
            capture_output=True,
            text=True,
        )

        assert result.returncode == 1
        assert "Usage: python -m clipmind.pipeline" in result.stdout
