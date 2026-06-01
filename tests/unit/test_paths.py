"""Tests for shared path and environment helpers."""

import os

from clipmind.paths import load_project_dotenv


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
