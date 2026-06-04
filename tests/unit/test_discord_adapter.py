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
    def test_post_success(self):
        responses.add(responses.POST, WEBHOOK_URL, status=200)

        dest = DiscordDestination(WEBHOOK_URL)
        dest.post(_make_clip())

        assert len(responses.calls) == 1

    def test_post_no_summary_skips(self):
        dest = DiscordDestination(WEBHOOK_URL)
        dest.post(_make_clip(summary_ja=None, summary_en=None))  # Should not raise.

    @responses.activate
    def test_post_http_error_raises(self):
        responses.add(responses.POST, WEBHOOK_URL, status=500, body="Server Error")

        dest = DiscordDestination(WEBHOOK_URL)
        with pytest.raises(Exception):
            dest.post(_make_clip())
