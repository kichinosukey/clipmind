"""Tests for scripts/install-local.sh."""

import os
import subprocess

import pytest

from clipmind.paths import PROJECT_ROOT


@pytest.fixture
def fake_home(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    return home


class TestInstallLocal:
    def test_install_writes_wrappers_with_repo_home(self, fake_home):
        env = {**os.environ, "HOME": str(fake_home)}
        script = PROJECT_ROOT / "scripts" / "install-local.sh"
        result = subprocess.run(
            ["/bin/zsh", str(script)],
            cwd=PROJECT_ROOT,
            env=env,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr + result.stdout

        run_wrapper = fake_home / ".local" / "bin" / "clipmind-run"
        repair_wrapper = fake_home / ".local" / "bin" / "clipmind-repair"
        assert run_wrapper.is_file() and os.access(run_wrapper, os.X_OK)
        assert repair_wrapper.is_file()

        text = run_wrapper.read_text(encoding="utf-8")
        assert str(PROJECT_ROOT) in text
        assert "exec" in text
        assert "clipmind-run" in text
