"""Clip dataclass — shared interface between pipeline and destination adapters."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Clip:
    """Normalized representation of a processed content item.

    Created by the pipeline after fetching source metadata.
    Populated progressively as transcription and summarization complete.
    Passed to destination adapters for posting.
    """

    source_type: str  # "youtube"
    url: str
    title: str
    author: str  # channel name
    author_url: str  # channel URL
    audio_path: str | None = None
    transcript: str | None = None
    summary_en: str | None = None
    summary_ja: str | None = None
    metadata: dict = field(default_factory=dict)
