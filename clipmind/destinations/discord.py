"""Discord destination adapter."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from clipmind.discord_client import post_clip_to_discord

if TYPE_CHECKING:
    from clipmind.clip import Clip


@dataclass(frozen=True)
class DiscordDestination:
    """Post a Clip summary to Discord via webhook."""

    webhook_url: str

    def post(self, clip: Clip) -> None:
        post_clip_to_discord(clip, self.webhook_url)
