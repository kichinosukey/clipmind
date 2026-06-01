"""Tests for native-host/clipmind_runner.py — runner state management and notifications."""

import json
import os
from pathlib import Path

import pytest


class TestNotify:
    def test_notify_calls_osascript(self, mocker):
        """notify() calls subprocess.run with correct osascript command."""
        import clipmind_runner

        mock_run = mocker.patch("clipmind_runner.subprocess.run")
        clipmind_runner.notify("Test Title", "Test Message")

        mock_run.assert_called_once()
        call_args = mock_run.call_args
        cmd = call_args[0][0]
        assert cmd[0] == "osascript"
        assert cmd[1] == "-e"
        assert "Test Title" in cmd[2]
        assert "Test Message" in cmd[2]

    def test_notify_silences_exception(self, mocker):
        """notify() does not raise even if subprocess fails."""
        import clipmind_runner

        mocker.patch(
            "clipmind_runner.subprocess.run",
            side_effect=OSError("osascript not found"),
        )
        # Should not raise
        clipmind_runner.notify("Title", "Message")


class TestUpdateStatus:
    def test_update_status_writes_json(self, tmp_path):
        """update_status writes correct JSON to the status file."""
        import clipmind_runner

        status_file = str(tmp_path / "status.json")
        data = {"status": "running", "url": "https://youtu.be/test"}
        clipmind_runner.update_status(status_file, data)

        with open(status_file) as f:
            written = json.load(f)
        assert written == data


class TestMain:
    def test_main_success(self, mocker, tmp_path):
        """run_pipeline success → status=completed + notification."""
        import clipmind_runner

        status_file = str(tmp_path / "status.json")
        mocker.patch("sys.argv", ["clipmind_runner.py", "https://youtu.be/abc", status_file])

        # Prevent chdir
        mock_chdir = mocker.patch("clipmind_runner.os.chdir")
        mock_load_env = mocker.patch("clipmind_runner.load_project_dotenv")

        mock_pipeline = mocker.patch(
            "clipmind.pipeline.run_pipeline",
            return_value={"title": "My Video", "transcript": "/tmp/t.txt", "delivery_results": {"discord": "ok"}},
        )
        mock_notify = mocker.patch("clipmind_runner.notify")

        clipmind_runner.main()

        # Verify pipeline was called with destinations
        mock_pipeline.assert_called_once_with("https://youtu.be/abc", destinations=["discord"])
        mock_chdir.assert_called_once_with(str(clipmind_runner.PROJECT_ROOT))
        mock_load_env.assert_called_once_with()

        # Verify status file
        with open(status_file) as f:
            status = json.load(f)
        assert status["status"] == "completed"
        assert status["title"] == "My Video"

        # Verify notification
        mock_notify.assert_called_once()
        assert "完了" in mock_notify.call_args[0][0]

    def test_main_pipeline_exit(self, mocker, tmp_path):
        """SystemExit from pipeline → status=error + error notification."""
        import clipmind_runner

        status_file = str(tmp_path / "status.json")
        mocker.patch("sys.argv", ["clipmind_runner.py", "https://youtu.be/abc", status_file])
        mocker.patch("clipmind_runner.os.chdir")
        mocker.patch("clipmind_runner.load_project_dotenv")
        mocker.patch(
            "clipmind.pipeline.run_pipeline",
            side_effect=SystemExit(1),
        )
        mock_notify = mocker.patch("clipmind_runner.notify")

        clipmind_runner.main()

        with open(status_file) as f:
            status = json.load(f)
        assert status["status"] == "error"
        assert "error" in status["error"].lower() or "exit" in status["error"].lower()

        mock_notify.assert_called()
        assert "エラー" in mock_notify.call_args[0][0]

    def test_main_pipeline_exception(self, mocker, tmp_path):
        """General exception → status=error + error message in notification."""
        import clipmind_runner

        status_file = str(tmp_path / "status.json")
        mocker.patch("sys.argv", ["clipmind_runner.py", "https://youtu.be/abc", status_file])
        mocker.patch("clipmind_runner.os.chdir")
        mocker.patch("clipmind_runner.load_project_dotenv")
        mocker.patch(
            "clipmind.pipeline.run_pipeline",
            side_effect=RuntimeError("Something broke"),
        )
        mock_notify = mocker.patch("clipmind_runner.notify")

        clipmind_runner.main()

        with open(status_file) as f:
            status = json.load(f)
        assert status["status"] == "error"
        assert "Something broke" in status["error"]

        mock_notify.assert_called()
