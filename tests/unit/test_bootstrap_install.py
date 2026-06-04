"""Tests for install.sh bootstrap (existing clone, no network clone)."""

import os
import subprocess

import pytest

from clipmind.paths import PROJECT_ROOT


@pytest.fixture
def fake_home(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    return home


class TestBootstrapInstall:
    def test_install_sh_syntax(self):
        for name in ("install.sh", "uninstall.sh"):
            script = PROJECT_ROOT / name
            result = subprocess.run(
                ["bash", "-n", str(script)],
                capture_output=True,
                text=True,
            )
            assert result.returncode == 0, result.stderr

    def test_bootstrap_uses_existing_linked_worktree(self, fake_home):
        """install.sh accepts an existing repo whose .git marker is a file."""
        assert (PROJECT_ROOT / ".git").is_file()
        env = {
            **os.environ,
            "HOME": str(fake_home),
            "CLIPMIND_HOME": str(PROJECT_ROOT),
            "CLIPMIND_SKIP_GIT_UPDATE": "1",
        }
        result = subprocess.run(
            ["bash", str(PROJECT_ROOT / "install.sh")],
            cwd=PROJECT_ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=300,
        )
        assert result.returncode == 0, result.stderr + result.stdout

        wrapper = fake_home / ".local" / "bin" / "clipmind-run"
        assert wrapper.is_file()
        assert str(PROJECT_ROOT) in wrapper.read_text(encoding="utf-8")

    def test_bootstrap_rejects_existing_non_repo_directory(self, fake_home, tmp_path):
        clipmind_home = tmp_path / "not-a-repo"
        clipmind_home.mkdir()
        env = {
            **os.environ,
            "HOME": str(fake_home),
            "CLIPMIND_HOME": str(clipmind_home),
            "CLIPMIND_SKIP_GIT_UPDATE": "1",
        }
        result = subprocess.run(
            ["bash", str(PROJECT_ROOT / "install.sh")],
            cwd=PROJECT_ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=300,
        )

        assert result.returncode != 0
        assert "exists but is not a git repository" in result.stderr
