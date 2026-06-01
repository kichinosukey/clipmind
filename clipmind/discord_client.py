#!/usr/bin/env python3
"""
Discord client utility for posting summarized content.

Usages:
- CLI:     python discord_client.py <title> <url> <channel> <ch_url> <summary> [webhook_url]
- Library: from clipmind.discord_client import post_clip_to_discord
"""

from __future__ import annotations

import os
import sys
from typing import TYPE_CHECKING

import requests

from clipmind.paths import load_project_dotenv
from clipmind.utils.log import log
from clipmind.utils.error import handle_error

if TYPE_CHECKING:
    from clipmind.clip import Clip

# ==== .env読込 ====
load_project_dotenv()

DEFAULT_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
MAX_LEN = 1900  # Discordメッセージ上限(2000)より安全マージン


# ==========================================================
# 内部ユーティリティ
# ==========================================================
def soft_split(text: str, max_len: int = MAX_LEN) -> list[str]:
    """テキストを自然な位置（句点・改行）で分割する。"""
    parts = []
    while text:
        if len(text) <= max_len:
            parts.append(text.strip())
            break
        chunk = text[:max_len]
        cut = max(chunk.rfind("。"), chunk.rfind("\n"))
        if cut == -1:
            cut = max_len
        parts.append(text[:cut + 1].strip())
        text = text[cut + 1:]
    return parts


def post_message(webhook_url: str, content: str) -> None:
    """Discordにメッセージを投稿する（内部用）。

    失敗時は例外をraiseする（sys.exitしない）。
    """
    log(f"[post_message] start, length={len(content)}")
    r = requests.post(webhook_url, json={"content": content}, timeout=10)
    log(f"[post_message] status_code={r.status_code}")
    if not r.ok:
        log(f"[post_message] response={r.text}", "ERROR")
        r.raise_for_status()
    log("[post_message] end")


# ==========================================================
# Clip対応API（destination adapterから呼び出す用）
# ==========================================================
def post_clip_to_discord(clip: Clip, webhook_url: str | None = None) -> None:
    """Clipオブジェクトの要約をDiscordに投稿する。

    失敗時は例外をraiseする（sys.exitしない）。
    pipelineのper-destination error isolationで使われることを想定。
    """
    webhook_url = webhook_url or DEFAULT_WEBHOOK_URL
    if not webhook_url:
        log("Webhook URL is not provided. Skipping Discord post.", "WARN")
        return

    summary = clip.summary_ja or clip.summary_en or ""
    if not summary:
        log("No summary available. Skipping Discord post.", "WARN")
        return

    log("[post_clip_to_discord] called")
    log(f"title={clip.title}")
    log(f"author={clip.author}")
    log(f"webhook_url={webhook_url[:40]}...")
    log(f"summary_length={len(summary)}")

    # ===== 分割 =====
    summary_parts = soft_split(summary)
    log(f"soft_split -> {len(summary_parts)} parts")

    # ===== 1件目 =====
    header = (
        f"\U0001f3ac: [{clip.title}]({clip.url})\n"
        f"\U0001f466: [{clip.author}]({clip.author_url})\n"
    )
    first = header + f"\U0001f4d3: {summary_parts[0]}"
    if len(first) > 2000:
        log(f"header込みで2000文字超過（{len(first)}）-> 再分割", "WARN")
        summary_parts = soft_split(header + f"\U0001f4d3: {summary}")
        first = summary_parts[0]

    post_message(webhook_url, first)
    log("[post_clip_to_discord] first message OK")

    # ===== 残り =====
    for i, part in enumerate(summary_parts[1:], start=2):
        label = f"\U0001f4c4 Part {i}/{len(summary_parts)}\n{part}"
        post_message(webhook_url, label)
        log(f"[post_clip_to_discord] Part {i} OK")

    log(f"[post_clip_to_discord] 完了（{len(summary_parts)}分割）")


# ==========================================================
# レガシーAPI（後方互換）
# ==========================================================
def post_to_discord(
    video_title: str,
    video_url: str,
    channel_name: str,
    channel_url: str,
    summary: str,
    webhook_url: str | None = None,
) -> None:
    """レガシーインターフェース。Clipを組み立ててpost_clip_to_discordに委譲。"""
    from clipmind.clip import Clip

    clip = Clip(
        source_type="youtube",
        url=video_url,
        title=video_title,
        author=channel_name,
        author_url=channel_url,
        summary_ja=summary,
    )
    post_clip_to_discord(clip, webhook_url)


# ==========================================================
# CLIエントリポイント
# ==========================================================
def main() -> None:
    """
    CLI用: python discord_client.py <title> <url> <channel> <ch_url> <summary> [webhook_url]
    """
    log("[main] start")

    if len(sys.argv) < 6:
        handle_error(
            "Insufficient arguments. Expected: title, url, channel_name, channel_url, summary [, webhook_url]"
        )

    video_title, video_url, channel_name, channel_url, summary = sys.argv[1:6]
    webhook_url = sys.argv[6] if len(sys.argv) > 6 else None

    try:
        post_to_discord(video_title, video_url, channel_name, channel_url, summary, webhook_url)
        log("[main] finished successfully")
    except Exception as e:
        handle_error("Discord posting failed in CLI mode", e)


if __name__ == "__main__":
    main()
