"""Slack destination adapter using Incoming Webhook + Block Kit."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import requests

from clipmind.discord_client import soft_split
from clipmind.paths import load_project_dotenv
from clipmind.utils.log import log

if TYPE_CHECKING:
    from clipmind.clip import Clip

load_project_dotenv()

DEFAULT_SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")
SLACK_TEXT_MAX = 3000  # Slack Block Kit text block limit


class SlackDestination:
    """Post a Clip summary to Slack via Incoming Webhook."""

    def post(self, clip: Clip) -> None:
        webhook_url = DEFAULT_SLACK_WEBHOOK_URL
        if not webhook_url:
            log("SLACK_WEBHOOK_URL is not set. Skipping Slack post.", "WARN")
            return

        summary = clip.summary_ja or clip.summary_en or ""
        if not summary:
            log("No summary available. Skipping Slack post.", "WARN")
            return

        log("[SlackDestination] posting")
        log(f"title={clip.title}")
        log(f"webhook_url={webhook_url[:40]}...")
        log(f"summary_length={len(summary)}")

        parts = soft_split(summary, max_len=SLACK_TEXT_MAX)
        log(f"soft_split -> {len(parts)} parts")

        # First message with header and metadata.
        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "ClipMind Summary", "emoji": True},
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*<{clip.url}|{clip.title}>*\nby <{clip.author_url}|{clip.author}>",
                },
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": parts[0]},
            },
            {
                "type": "context",
                "elements": [{"type": "mrkdwn", "text": "Summarized by ClipMind"}],
            },
        ]

        self._send(webhook_url, {"blocks": blocks})
        log("[SlackDestination] first message OK")

        # Remaining parts as follow-up messages.
        for i, part in enumerate(parts[1:], start=2):
            payload = {
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*Part {i}/{len(parts)}*\n{part}",
                        },
                    },
                ],
            }
            self._send(webhook_url, payload)
            log(f"[SlackDestination] Part {i} OK")

        log(f"[SlackDestination] 完了（{len(parts)}分割）")

    @staticmethod
    def _send(webhook_url: str, payload: dict) -> None:
        """Send a payload to a Slack Incoming Webhook.

        Raises on HTTP errors so the pipeline's per-destination
        error isolation can catch and report partial failures.
        """
        r = requests.post(webhook_url, json=payload, timeout=10)
        if not r.ok:
            log(f"[SlackDestination] error: {r.status_code} {r.text}", "ERROR")
            r.raise_for_status()
