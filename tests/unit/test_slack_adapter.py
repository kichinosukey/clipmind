"""Tests for clipmind.destinations.slack — SlackDestination adapter."""

import json

import pytest
import responses

from clipmind.clip import Clip
from clipmind.destinations.slack import SlackDestination

SLACK_WEBHOOK = "https://hooks.slack.com/services/T00/B00/xxxx"


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


class TestSlackDestination:
    @responses.activate
    def test_post_success(self):
        responses.add(responses.POST, SLACK_WEBHOOK, status=200, body="ok")

        dest = SlackDestination(SLACK_WEBHOOK)
        dest.post(_make_clip())

        assert len(responses.calls) == 1
        body = json.loads(responses.calls[0].request.body)
        assert "blocks" in body
        # Header block.
        assert body["blocks"][0]["type"] == "header"
        # Section with title link.
        assert "Test Video" in body["blocks"][1]["text"]["text"]
        # Section with summary.
        assert "日本語の要約テスト" in body["blocks"][2]["text"]["text"]

    def test_post_no_summary_skips(self):
        dest = SlackDestination(SLACK_WEBHOOK)
        dest.post(_make_clip(summary_ja=None, summary_en=None))  # Should not raise.

    @responses.activate
    def test_post_long_summary_splits(self):
        responses.add(responses.POST, SLACK_WEBHOOK, status=200, body="ok")

        long_summary = "あ" * 3000 + "。" + "い" * 500
        dest = SlackDestination(SLACK_WEBHOOK)
        dest.post(_make_clip(summary_ja=long_summary))

        # Should be at least 2 messages due to chunking.
        assert len(responses.calls) >= 2

    @responses.activate
    def test_post_http_error_raises(self):
        responses.add(responses.POST, SLACK_WEBHOOK, status=403, body="invalid_token")

        dest = SlackDestination(SLACK_WEBHOOK)
        with pytest.raises(Exception):
            dest.post(_make_clip())

    @responses.activate
    def test_post_uses_summary_en_fallback(self):
        responses.add(responses.POST, SLACK_WEBHOOK, status=200, body="ok")

        dest = SlackDestination(SLACK_WEBHOOK)
        dest.post(_make_clip(summary_ja=None, summary_en="English fallback"))

        assert len(responses.calls) == 1
        body = json.loads(responses.calls[0].request.body)
        assert "English fallback" in body["blocks"][2]["text"]["text"]
