#!/usr/bin/env python3
"""
Discord client utility for posting summarized YouTube transcripts.

Usages:
- CLI:     python discord_client.py <title> <url> <channel> <ch_url> <summary> [webhook_url]
- Library: from yt_full.discord_client import post_to_discord
"""

import os
import sys
import requests
from dotenv import load_dotenv
from clipmind.utils.log import log
from clipmind.utils.error import handle_error

# ==== .env読込 ====
load_dotenv()

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
    """Discordにメッセージを投稿する（内部用）"""
    log(f"[post_message] start, length={len(content)}")
    try:
        r = requests.post(webhook_url, json={"content": content}, timeout=10)
        log(f"[post_message] status_code={r.status_code}")
        if not r.ok:
            log(f"[post_message] response={r.text}", "ERROR")
            r.raise_for_status()
    except Exception as e:
        handle_error("Failed to post message to Discord", e)
    log("[post_message] end")


# ==========================================================
# 外部API（pipelineなどから呼び出す用）
# ==========================================================
def post_to_discord(
    video_title: str,
    video_url: str,
    channel_name: str,
    channel_url: str,
    summary: str,
    webhook_url: str | None = None,
) -> None:
    """
    Discordに日本語要約を投稿する。

    Args:
        video_title (str): 動画タイトル
        video_url (str): YouTube動画URL
        channel_name (str): チャンネル名
        channel_url (str): チャンネルURL
        summary (str): 投稿したい要約本文
        webhook_url (str | None): Discord Webhook URL（未指定なら.envから）
    """
    webhook_url = webhook_url or DEFAULT_WEBHOOK_URL
    if not webhook_url:
        handle_error("Webhook URL is not provided (.envにDISCORD_WEBHOOK_URLを設定してください)")

    log("[post_to_discord] called")
    log(f"video_title={video_title}")
    log(f"channel_name={channel_name}")
    log(f"webhook_url={webhook_url[:40]}...")
    log(f"summary_length={len(summary)}")

    # ===== 分割 =====
    summary_parts = soft_split(summary)
    log(f"soft_split → {len(summary_parts)} parts")

    # ===== 1件目 =====
    header = (
        f"🎥: [{video_title}]({video_url})\n"
        f"👦: [{channel_name}]({channel_url})\n"
    )
    first = header + f"📓: {summary_parts[0]}"
    if len(first) > 2000:
        log(f"header込みで2000文字超過（{len(first)}）→再分割", "WARN")
        summary_parts = soft_split(header + f"📓: {summary}")
        first = summary_parts[0]

    try:
        post_message(webhook_url, first)
        log("[post_to_discord] first message OK")
    except Exception as e:
        handle_error("Failed to post first Discord message", e)

    # ===== 残り =====
    if len(summary_parts) > 1:
        for i, part in enumerate(summary_parts[1:], start=2):
            label = f"📄 Part {i}/{len(summary_parts)}\n{part}"
            try:
                post_message(webhook_url, label)
                log(f"[post_to_discord] Part {i} OK")
            except Exception as e:
                handle_error(f"Failed to post Part {i}", e)
    else:
        log("[post_to_discord] single-part message only")

    log(f"[post_to_discord] 完了（{len(summary_parts)}分割）")


# ==========================================================
# CLIエントリポイント
# ==========================================================
def main() -> None:
    """
    CLI用: python discord_client.py <title> <url> <channel> <ch_url> <summary> [webhook_url]

    Note:
        summaryは短文テストを推奨。
        長文（>2000文字）は自動分割される。
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

