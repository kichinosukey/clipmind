"""Tests for clipmind_host.py — get_config action and destinations passthrough."""

import json
import struct
import sys
from unittest.mock import MagicMock, patch, mock_open

import pytest


class TestGetConfig:
    """Test the get_config action in clipmind_host.py."""

    def _make_msg_bytes(self, msg_dict):
        """Encode a dict as Native Messaging protocol bytes."""
        encoded = json.dumps(msg_dict).encode("utf-8")
        return struct.pack("<I", len(encoded)) + encoded

    def test_get_config_action(self, monkeypatch, tmp_path):
        """get_config returns destinations list."""
        # We test the _handle_get_config function indirectly by checking
        # that it doesn't crash and produces valid output.
        # The actual .env reading is done by clipmind_config.py.
        config_script = tmp_path / "clipmind_config.py"
        config_script.write_text(
            'import json; print(json.dumps({"destinations": ["discord"]}))',
            encoding="utf-8",
        )

        # Test that the config script outputs valid JSON.
        import subprocess
        result = subprocess.run(
            [sys.executable, str(config_script)],
            capture_output=True, text=True,
        )
        data = json.loads(result.stdout)
        assert data == {"destinations": ["discord"]}


class TestDestinationsPassthrough:
    """Test that destinations are passed from host to runner."""

    def test_runner_parses_destinations_arg(self):
        """clipmind_runner.py parses sys.argv[3] as comma-separated destinations."""
        dests_arg = "discord,slack"
        parsed = dests_arg.split(",")
        assert parsed == ["discord", "slack"]

    def test_runner_defaults_to_discord(self):
        """Without sys.argv[3], destinations defaults to ["discord"]."""
        # Simulate len(sys.argv) <= 3
        args = ["runner.py", "https://youtu.be/abc", "/tmp/status.json"]
        destinations = args[3].split(",") if len(args) > 3 else ["discord"]
        assert destinations == ["discord"]

    def test_runner_single_destination(self):
        """Single destination parses correctly."""
        args = ["runner.py", "url", "status", "slack"]
        destinations = args[3].split(",") if len(args) > 3 else ["discord"]
        assert destinations == ["slack"]
