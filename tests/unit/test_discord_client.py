"""Tests for clipmind.discord_client — post_message() and post_to_discord()."""

import pytest
import responses

from clipmind.discord_client import post_message, post_to_discord

WEBHOOK_URL = "https://discord.com/api/webhooks/test/token"


class TestPostMessage:
    @responses.activate
    def test_post_message_success(self):
        """200 response completes without error."""
        responses.add(responses.POST, WEBHOOK_URL, status=200)
        post_message(WEBHOOK_URL, "Hello Discord")

    @responses.activate
    def test_post_message_payload(self):
        """JSON body is {"content": content} with timeout=10."""
        responses.add(responses.POST, WEBHOOK_URL, status=200)
        post_message(WEBHOOK_URL, "test content")

        assert len(responses.calls) == 1
        import json

        body = json.loads(responses.calls[0].request.body)
        assert body == {"content": "test content"}

    @responses.activate
    def test_post_message_http_error(self):
        """Non-OK response raises HTTPError (not SystemExit)."""
        responses.add(responses.POST, WEBHOOK_URL, status=400, body="Bad Request")
        with pytest.raises(Exception):
            post_message(WEBHOOK_URL, "bad message")


class TestPostToDiscord:
    @responses.activate
    def test_post_to_discord_no_webhook_skips(self, mocker):
        """webhook_url=None and no env → no HTTP call."""
        mocker.patch("clipmind.discord_client.DEFAULT_WEBHOOK_URL", None)
        post_to_discord("title", "url", "channel", "ch_url", "summary")
        assert len(responses.calls) == 0

    @responses.activate
    def test_post_to_discord_short_summary(self):
        """Short summary posts a single message with header + summary."""
        responses.add(responses.POST, WEBHOOK_URL, status=200)
        post_to_discord(
            "Video Title",
            "https://youtu.be/abc",
            "Channel",
            "https://youtube.com/@Channel",
            "Short summary text.",
            webhook_url=WEBHOOK_URL,
        )
        assert len(responses.calls) == 1

    @responses.activate
    def test_post_to_discord_long_summary(self):
        """Long summary is split into multiple messages with Part labels."""
        responses.add(responses.POST, WEBHOOK_URL, status=200)
        long_summary = "あ" * 1900 + "。" + "い" * 500
        post_to_discord(
            "Title",
            "https://youtu.be/abc",
            "Ch",
            "https://youtube.com/@Ch",
            long_summary,
            webhook_url=WEBHOOK_URL,
        )
        assert len(responses.calls) >= 2

    @responses.activate
    def test_post_to_discord_header_format(self):
        """First message contains video title, URL, and channel name."""
        responses.add(responses.POST, WEBHOOK_URL, status=200)
        post_to_discord(
            "My Video",
            "https://youtu.be/xyz",
            "My Channel",
            "https://youtube.com/@MyChannel",
            "Summary content here.",
            webhook_url=WEBHOOK_URL,
        )
        import json

        body = json.loads(responses.calls[0].request.body)
        content = body["content"]
        assert "My Video" in content
        assert "https://youtu.be/xyz" in content
        assert "My Channel" in content
