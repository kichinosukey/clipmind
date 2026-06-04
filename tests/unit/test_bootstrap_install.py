"""Tests for install.sh bootstrap (existing clone, no network clone)."""

import os
import subprocess
import tempfile
from pathlib import Path

import pytest

from clipmind.paths import PROJECT_ROOT


def run_git(*args, cwd=PROJECT_ROOT):
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )


def create_fake_python(repo):
    fake_python = repo / ".venv" / "bin" / "python"
    fake_python.parent.mkdir(parents=True)
    fake_python.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    fake_python.chmod(0o755)


def create_minimal_install_repo(repo):
    (repo / "scripts").mkdir()
    (repo / "requirements.txt").touch()
    for path in (
        repo / "clipmind-run",
        repo / "clipmind-repair",
        repo / "scripts" / "install-local.sh",
    ):
        path.write_text("#!/bin/zsh\nexit 0\n", encoding="utf-8")
        path.chmod(0o755)
    create_fake_python(repo)


@pytest.fixture
def fake_home(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    return home


@pytest.fixture
def linked_worktree(tmp_path):
    worktree = tmp_path / "linked-worktree"
    run_git("worktree", "add", "--detach", str(worktree), "HEAD")
    create_fake_python(worktree)
    try:
        yield worktree
    finally:
        run_git("worktree", "remove", str(worktree))


@pytest.fixture
def feature_repo(tmp_path):
    origin = tmp_path / "origin.git"
    repo = tmp_path / "repo"
    run_git("init", "--bare", str(origin))
    run_git("init", "--initial-branch=main", str(repo))
    run_git("config", "user.email", "tests@example.com", cwd=repo)
    run_git("config", "user.name", "ClipMind Tests", cwd=repo)
    create_minimal_install_repo(repo)
    run_git(
        "add",
        "requirements.txt",
        "clipmind-run",
        "clipmind-repair",
        "scripts/install-local.sh",
        cwd=repo,
    )
    run_git("commit", "-m", "initial", cwd=repo)
    run_git("remote", "add", "origin", str(origin), cwd=repo)
    run_git("push", "-u", "origin", "main", cwd=repo)
    run_git("switch", "-c", "feature", cwd=repo)
    return repo


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

    def test_bootstrap_uses_existing_linked_worktree(self, fake_home, linked_worktree):
        """install.sh accepts an existing repo whose .git marker is a file."""
        assert (linked_worktree / ".git").is_file()
        env = {
            **os.environ,
            "HOME": str(fake_home),
            "CLIPMIND_HOME": str(linked_worktree),
            "CLIPMIND_SKIP_GIT_UPDATE": "1",
            "GIT_DIR": run_git("rev-parse", "--absolute-git-dir").stdout.strip(),
            "GIT_WORK_TREE": str(PROJECT_ROOT),
        }
        result = subprocess.run(
            ["bash", str(PROJECT_ROOT / "install.sh")],
            cwd=linked_worktree,
            env=env,
            capture_output=True,
            text=True,
            timeout=300,
        )
        assert result.returncode == 0, result.stderr + result.stdout

        wrapper = fake_home / ".local" / "bin" / "clipmind-run"
        assert wrapper.is_file()
        assert str(linked_worktree) in wrapper.read_text(encoding="utf-8")

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

    def test_bootstrap_rejects_subdirectory_inside_repo(self, fake_home):
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT) as clipmind_home:
            create_fake_python(Path(clipmind_home))
            env = {
                **os.environ,
                "HOME": str(fake_home),
                "CLIPMIND_HOME": clipmind_home,
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

    def test_bootstrap_fetches_without_switching_feature_branch(self, fake_home, feature_repo):
        env = {
            **os.environ,
            "HOME": str(fake_home),
            "CLIPMIND_HOME": str(feature_repo),
            "CLIPMIND_BRANCH": "main",
        }
        result = subprocess.run(
            ["bash", str(PROJECT_ROOT / "install.sh")],
            cwd=feature_repo,
            env=env,
            capture_output=True,
            text=True,
            timeout=300,
        )

        assert result.returncode == 0, result.stderr + result.stdout
        assert run_git("branch", "--show-current", cwd=feature_repo).stdout.strip() == "feature"
        assert "current branch is feature; update skipped" in result.stdout

    def test_bootstrap_rejects_non_repo_with_ambient_git_environment(
        self, fake_home, tmp_path
    ):
        clipmind_home = tmp_path / "not-a-repo"
        clipmind_home.mkdir()
        create_fake_python(clipmind_home)
        git_dir = run_git("rev-parse", "--absolute-git-dir").stdout.strip()
        env = {
            **os.environ,
            "HOME": str(fake_home),
            "CLIPMIND_HOME": str(clipmind_home),
            "CLIPMIND_SKIP_GIT_UPDATE": "1",
            "GIT_DIR": git_dir,
            "GIT_WORK_TREE": str(clipmind_home),
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
