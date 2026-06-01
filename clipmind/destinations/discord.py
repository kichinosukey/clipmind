"""Discord destination adapter."""

from __future__ import annotations

from typing import TYPE_CHECKING

from clipmind.discord_client import post_clip_to_discord

if TYPE_CHECKING:
    from clipmind.clip import Clip


class DiscordDestination:
    """Post a Clip summary to Discord via webhook."""

    def post(self, clip: Clip) -> None:
        post_clip_to_discord(clip)
