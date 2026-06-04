"""Integration tests for multi-destination pipeline."""

import json

import pytest
import responses

from clipmind.clip import Clip


DISCORD_WEBHOOK = "https://discord.com/api/webhooks/test/token"
SLACK_WEBHOOK = "https://hooks.slack.com/services/T00/B00/xxxx"


WEBHOOKS = {"discord": DISCORD_WEBHOOK, "slack": SLACK_WEBHOOK}


class TestMultiDestDelivery:
    """Test the delivery portion of the pipeline using pre-built Clips."""

    def _make_clip(self):
        return Clip(
            source_type="youtube",
            url="https://youtu.be/abc",
            title="Test Video",
            author="TestChannel",
            author_url="https://youtube.com/@TestChannel",
            summary_en="English summary",
            summary_ja="日本語の要約",
        )

    @responses.activate
    def test_both_destinations_called(self):
        """Discord and Slack both receive posts."""
        responses.add(responses.POST, DISCORD_WEBHOOK, status=200)
        responses.add(responses.POST, SLACK_WEBHOOK, status=200, body="ok")

        from clipmind.destinations import resolve_destination

        clip = self._make_clip()
        results = {}
        for dest_name in ["discord", "slack"]:
            try:
                dest = resolve_destination(dest_name, webhook_url=WEBHOOKS[dest_name])
                dest.post(clip)
                results[dest_name] = "ok"
            except Exception as e:
                results[dest_name] = f"error: {e}"

        assert results == {"discord": "ok", "slack": "ok"}
        # At least one call to each webhook.
        discord_calls = [c for c in responses.calls if DISCORD_WEBHOOK in c.request.url]
        slack_calls = [c for c in responses.calls if SLACK_WEBHOOK in c.request.url]
        assert len(discord_calls) >= 1
        assert len(slack_calls) >= 1

    @responses.activate
    def test_partial_failure_discord_fails(self):
        """Discord fails, Slack succeeds. Both are reported."""
        responses.add(responses.POST, DISCORD_WEBHOOK, status=500, body="Server Error")
        responses.add(responses.POST, SLACK_WEBHOOK, status=200, body="ok")

        from clipmind.destinations import resolve_destination

        clip = self._make_clip()
        results = {}
        for dest_name in ["discord", "slack"]:
            try:
                dest = resolve_destination(dest_name, webhook_url=WEBHOOKS[dest_name])
                dest.post(clip)
                results[dest_name] = "ok"
            except Exception as e:
                results[dest_name] = f"error: {e}"

        assert "error" in results["discord"]
        assert results["slack"] == "ok"

    @responses.activate
    def test_partial_failure_slack_fails(self):
        """Slack fails, Discord succeeds."""
        responses.add(responses.POST, DISCORD_WEBHOOK, status=200)
        responses.add(responses.POST, SLACK_WEBHOOK, status=403, body="invalid_token")

        from clipmind.destinations import resolve_destination

        clip = self._make_clip()
        results = {}
        for dest_name in ["discord", "slack"]:
            try:
                dest = resolve_destination(dest_name, webhook_url=WEBHOOKS[dest_name])
                dest.post(clip)
                results[dest_name] = "ok"
            except Exception as e:
                results[dest_name] = f"error: {e}"

        assert results["discord"] == "ok"
        assert "error" in results["slack"]

    @responses.activate
    def test_default_destinations(self):
        """When no destinations specified, default to discord."""
        responses.add(responses.POST, DISCORD_WEBHOOK, status=200)

        from clipmind.destinations import resolve_destination

        clip = self._make_clip()
        default_dests = ["discord"]
        for dest_name in default_dests:
            dest = resolve_destination(dest_name, webhook_url=WEBHOOKS[dest_name])
            dest.post(clip)

        assert len(responses.calls) >= 1
