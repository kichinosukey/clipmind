"""Tests for native-host/clipmind_host.py — Native Messaging protocol."""

import io
import json
import struct
import types
from pathlib import Path

import pytest


class TestReadMessage:
    def test_read_message_valid(self, mocker):
        """4-byte length + JSON payload is read correctly."""
        import clipmind_host

        payload = json.dumps({"url": "https://youtu.be/abc"}).encode("utf-8")
        raw = struct.pack("<I", len(payload)) + payload

        fake_stdin = types.SimpleNamespace(buffer=io.BytesIO(raw))
        mocker.patch.object(clipmind_host, "sys", wraps=clipmind_host.sys)
        mocker.patch("clipmind_host.sys.stdin", fake_stdin)

        result = clipmind_host.read_message()
        assert result == {"url": "https://youtu.be/abc"}

    def test_read_message_empty(self, mocker):
        """Empty stdin returns None."""
        import clipmind_host

        fake_stdin = types.SimpleNamespace(buffer=io.BytesIO(b""))
        mocker.patch("clipmind_host.sys.stdin", fake_stdin)

        result = clipmind_host.read_message()
        assert result is None


class TestSendMessage:
    def test_send_message_format(self, mocker):
        """Output follows binary protocol: 4-byte little-endian length + JSON."""
        import clipmind_host

        buf = io.BytesIO()
        fake_stdout = types.SimpleNamespace(buffer=buf)
        mocker.patch("clipmind_host.sys.stdout", fake_stdout)

        clipmind_host.send_message({"status": "ok"})

        buf.seek(0)
        raw_length = buf.read(4)
        length = struct.unpack("<I", raw_length)[0]
        data = buf.read(length)
        msg = json.loads(data.decode("utf-8"))
        assert msg == {"status": "ok"}


def _read_native_message(buf):
    """Helper to read a Native Messaging response from a BytesIO buffer."""
    buf.seek(0)
    raw_length = buf.read(4)
    length = struct.unpack("<I", raw_length)[0]
    data = buf.read(length)
    return json.loads(data.decode("utf-8"))


class TestMain:
    def test_main_no_url(self, mocker):
        """Missing URL in message → error response."""
        import clipmind_host

        mocker.patch.object(clipmind_host, "read_message", return_value={"action": "test"})

        buf = io.BytesIO()
        fake_stdout = types.SimpleNamespace(buffer=buf)
        mocker.patch("clipmind_host.sys.stdout", fake_stdout)

        clipmind_host.main()

        msg = _read_native_message(buf)
        assert msg["status"] == "error"
        assert "URL" in msg["error"] or "url" in msg["error"].lower()

    def test_main_no_message(self, mocker):
        """No message from stdin → error response."""
        import clipmind_host

        mocker.patch.object(clipmind_host, "read_message", return_value=None)

        buf = io.BytesIO()
        fake_stdout = types.SimpleNamespace(buffer=buf)
        mocker.patch("clipmind_host.sys.stdout", fake_stdout)

        clipmind_host.main()

        msg = _read_native_message(buf)
        assert msg["status"] == "error"

    def test_main_venv_not_found(self, mocker, tmp_path):
        """venv python not found → error response."""
        import clipmind_host

        mocker.patch.object(
            clipmind_host, "read_message",
            return_value={"url": "https://youtu.be/abc"},
        )
        mocker.patch("clipmind_host.os.path.exists", return_value=False)
        mocker.patch("clipmind_host.os.makedirs")
        mocker.patch("builtins.open", mocker.mock_open())

        buf = io.BytesIO()
        fake_stdout = types.SimpleNamespace(buffer=buf)
        mocker.patch("clipmind_host.sys.stdout", fake_stdout)

        clipmind_host.main()

        msg = _read_native_message(buf)
        assert msg["status"] == "error"
        assert "venv" in msg["error"]

    def test_main_success(self, mocker, tmp_path):
        """Valid URL → Popen launched + 'started' response."""
        import clipmind_host

        mocker.patch.object(
            clipmind_host, "read_message",
            return_value={"url": "https://youtu.be/abc"},
        )

        original_exists = clipmind_host.os.path.exists
        mocker.patch(
            "clipmind_host.os.path.exists",
            side_effect=lambda p: True if ".venv" in str(p) else original_exists(p),
        )

        mock_popen = mocker.patch("clipmind_host.subprocess.Popen")

        buf = io.BytesIO()
        fake_stdout = types.SimpleNamespace(buffer=buf)
        mocker.patch("clipmind_host.sys.stdout", fake_stdout)

        clipmind_host.main()

        mock_popen.assert_called_once()
        call_args = mock_popen.call_args
        project_root = Path(clipmind_host.__file__).resolve().parent.parent
        assert call_args.args[0][0] == str(project_root / ".venv" / "bin" / "python")
        assert call_args.args[0][1] == str(project_root / "native-host" / "clipmind_runner.py")
        assert call_args.kwargs["cwd"] == str(project_root)

        msg = _read_native_message(buf)
        assert msg["status"] == "started"
        assert "job_id" in msg
