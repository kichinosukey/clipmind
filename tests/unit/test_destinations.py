"""Tests for clipmind.destinations — adapter registry."""

import pytest

from clipmind.destinations import resolve_destination
from clipmind.destinations.discord import DiscordDestination
from clipmind.destinations.slack import SlackDestination


class TestResolveDestination:
    def test_resolve_discord(self):
        dest = resolve_destination("discord", webhook_url="discord-hook")
        assert isinstance(dest, DiscordDestination)
        assert dest.webhook_url == "discord-hook"

    def test_resolve_slack(self):
        dest = resolve_destination("slack", webhook_url="slack-hook")
        assert isinstance(dest, SlackDestination)
        assert dest.webhook_url == "slack-hook"

    def test_resolve_unknown_raises(self):
        with pytest.raises(KeyError, match="Unknown destination"):
            resolve_destination("notion", webhook_url="hook")

    def test_missing_webhook_raises(self):
        with pytest.raises(ValueError, match="Webhook"):
            resolve_destination("discord", webhook_url=None)
