"""Destination adapter registry."""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Protocol

if TYPE_CHECKING:
    from clipmind.clip import Clip


class DestinationAdapter(Protocol):
    """Interface for posting a Clip to a destination."""

    def post(self, clip: Clip) -> None: ...


_ADAPTERS: dict[str, Callable[..., DestinationAdapter]] = {}


def register(name: str, cls: Callable[..., DestinationAdapter]) -> None:
    _ADAPTERS[name] = cls


def resolve_destination(name: str, *, webhook_url: str | None) -> DestinationAdapter:
    """Return an adapter instance for the given destination name.

    Raises ``KeyError`` if the destination is unknown.
    """
    if name not in _ADAPTERS:
        raise KeyError(f"Unknown destination: {name!r}. Available: {list(_ADAPTERS)}")
    if not webhook_url:
        raise ValueError(f"Webhook is not configured for destination: {name}")
    return _ADAPTERS[name](webhook_url=webhook_url)


# Auto-register built-in adapters on import.
from clipmind.destinations.discord import DiscordDestination  # noqa: E402
from clipmind.destinations.slack import SlackDestination  # noqa: E402

register("discord", DiscordDestination)
register("slack", SlackDestination)
