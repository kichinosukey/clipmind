"""Tests for clipmind.destinations — adapter registry."""

import pytest

from clipmind.destinations import resolve_destination
from clipmind.destinations.discord import DiscordDestination
from clipmind.destinations.slack import SlackDestination


class TestResolveDestination:
    def test_resolve_discord(self):
        dest = resolve_destination("discord")
        assert isinstance(dest, DiscordDestination)

    def test_resolve_slack(self):
        dest = resolve_destination("slack")
        assert isinstance(dest, SlackDestination)

    def test_resolve_unknown_raises(self):
        with pytest.raises(KeyError, match="Unknown destination"):
            resolve_destination("notion")
