"""Tests for clipmind.destinations.discord — DiscordDestination adapter."""

import pytest
import responses

from clipmind.clip import Clip
from clipmind.destinations.discord import DiscordDestination

WEBHOOK_URL = "https://discord.com/api/webhooks/test/token"


def _make_clip(**overrides):
    defaults = dict(
        source_type="youtube",
        url="https://youtu.be/abc",
        title="Test Video",
        author="TestChannel",
        author_url="https://youtube.com/@TestChannel",
        summary_ja="日本語の要約テスト",
    )
    defaults.update(overrides)
    return Clip(**defaults)


class TestDiscordDestination:
    @responses.activate
    def test_post_success(self, monkeypatch):
        monkeypatch.setenv("DISCORD_WEBHOOK_URL", WEBHOOK_URL)
        # Reload the module-level default after env change.
        import clipmind.discord_client as dc
        monkeypatch.setattr(dc, "DEFAULT_WEBHOOK_URL", WEBHOOK_URL)

        responses.add(responses.POST, WEBHOOK_URL, status=200)

        dest = DiscordDestination()
        dest.post(_make_clip())

        assert len(responses.calls) == 1

    def test_post_no_webhook_skips(self, monkeypatch):
        import clipmind.discord_client as dc
        monkeypatch.setattr(dc, "DEFAULT_WEBHOOK_URL", None)

        dest = DiscordDestination()
        dest.post(_make_clip())  # Should not raise.

    def test_post_no_summary_skips(self, monkeypatch):
        import clipmind.discord_client as dc
        monkeypatch.setattr(dc, "DEFAULT_WEBHOOK_URL", WEBHOOK_URL)

        dest = DiscordDestination()
        dest.post(_make_clip(summary_ja=None, summary_en=None))  # Should not raise.

    @responses.activate
    def test_post_http_error_raises(self, monkeypatch):
        import clipmind.discord_client as dc
        monkeypatch.setattr(dc, "DEFAULT_WEBHOOK_URL", WEBHOOK_URL)

        responses.add(responses.POST, WEBHOOK_URL, status=500, body="Server Error")

        dest = DiscordDestination()
        with pytest.raises(Exception):
            dest.post(_make_clip())
