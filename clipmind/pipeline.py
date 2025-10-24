#!/usr/bin/env python3
"""
clipmind.pipeline
----------------

YouTube動画URLを起点に、以下の一連の処理を自動実行する統合パイプライン。

1. YouTubeから音声をダウンロード（yt-dlp）
2. Whisper.cppによる文字起こし
3. LLMによる要約（英語）
4. LLMによる日本語翻訳
5. Discordへの投稿

想定用途:
- Alfred Workflow からの呼び出し
- RSS / cron / Webhook などの自動トリガー
- CLIスクリプトや他ツールからの直接呼び出し
"""

import os
import json
import subprocess
from dotenv import load_dotenv

from clipmind.summarizer import summarize_text
from clipmind.discord_client import post_to_discord
from clipmind.utils.log import log
from clipmind.utils.error import handle_error

# ==== .env 読み込み ====
load_dotenv()


def run_pipeline(
    url: str,
    outroot: str | None = None,
    whisper_bin: str | None = None,
    whisper_model: str | None = None,
) -> dict:
    """YouTube URLを入力として、要約〜Discord投稿までを自動実行する。

    Args:
        url (str): 対象のYouTube動画URL。
        outroot (str | None): 出力ルートディレクトリ（未指定なら .env の OUTROOT を使用）。
        whisper_bin (str | None): whisper-cli の実行パス（未指定なら .env またはデフォルト）。
        whisper_model (str | None): Whisperモデルファイルのパス（未指定なら .env またはデフォルト）。

    Returns:
        dict: 実行結果情報を含む辞書。
    """
    try:
        # ==== 出力先の決定 ====
        outroot = outroot or os.getenv("OUTROOT", "~/clipmind/data")
        outroot = os.path.expanduser(outroot)
        os.makedirs(outroot, exist_ok=True)
        log(f"Output root directory: {outroot}")

        # ==== Whisper設定 ====
        whisper_bin = whisper_bin or os.getenv("WHISPER_BIN", "~/whisper.cpp/build/bin/whisper-cli")
        whisper_model = whisper_model or os.getenv("WHISPER_MODEL", "~/whisper.cpp/models/ggml-base.en.bin")
        whisper_bin = os.path.expanduser(whisper_bin)
        whisper_model = os.path.expanduser(whisper_model)
        log(f"Using Whisper binary: {whisper_bin}")
        log(f"Using Whisper model: {whisper_model}")

        log(f"Pipeline started for: {url}")

        # ==== 1. 動画メタデータ取得 ====
        log("Fetching video metadata...")
        result = subprocess.run(
            ["yt-dlp", "-J", url],
            capture_output=True, text=True, check=True
        )
        info = json.loads(result.stdout)

        video_title = info.get("title", "unknown_title")
        channel_name = info.get("channel", "unknown_channel")
        channel_url = info.get("channel_url", "")

        # ==== 2. ダウンロードディレクトリ設定 ====
        safe_title = "".join(c if c.isalnum() or c in " _-" else "_" for c in video_title)[:80]
        outdir = os.path.join(outroot, channel_name, safe_title)
        os.makedirs(outdir, exist_ok=True)
        wav_path = os.path.join(outdir, f"{safe_title}.wav")

        # ==== 3. 音声ダウンロード ====
        log(f"Downloading audio to {wav_path} ...")
        subprocess.run([
            "yt-dlp", "--no-playlist", "-f", "bestaudio", "-x",
            "--audio-format", "wav", "-o", wav_path, url
        ], check=True)

        # ==== 4. Whisper文字起こし ====
        txt_out = wav_path.replace(".wav", ".txt")
        log("Transcribing with Whisper...")
        subprocess.run([
            whisper_bin, "-m", whisper_model, "-f", wav_path,
            "-otxt", "-of", txt_out[:-4]
        ], check=True)

        if not os.path.exists(txt_out):
            raise FileNotFoundError(f"Transcription output not found: {txt_out}")

        # ==== 5. 要約 ====
        with open(txt_out, "r", encoding="utf-8") as f:
            text = f.read()
        if not text.strip():
            raise ValueError("Transcription file is empty.")

        log("Summarizing in English...")
        summary_en = summarize_text(text, "summarize")
        log(f"DEBUG: summary_en length = {len(summary_en)}")

        summary_en_path = txt_out.replace(".txt", "_summary.txt")
        with open(summary_en_path, "w", encoding="utf-8") as f:
            f.write(summary_en)
        log(f"English summary written to: {summary_en_path}")

        # ==== 6. 翻訳 ====
        log("Translating to Japanese...")
        summary_ja = summarize_text(summary_en, "translate")
        log(f"DEBUG: summary_ja length = {len(summary_ja)}")

        summary_ja_path = txt_out.replace(".txt", "_summary_ja.txt")
        with open(summary_ja_path, "w", encoding="utf-8") as f:
            f.write(summary_ja)
        log(f"Japanese summary written to: {summary_ja_path}")

        # ==== 7. metadata.json ====
        metadata = {
            "title": video_title,
            "channel": channel_name,
            "url": url,
            "summary_en_len": len(summary_en),
            "summary_ja_len": len(summary_ja),
        }
        with open(os.path.join(outdir, "metadata.json"), "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        log(f"Metadata written to: {outdir}/metadata.json")

        # ==== 8. Discord投稿 ====
        log("Posting to Discord...")
        post_to_discord(
            video_title=video_title,
            video_url=url,
            channel_name=channel_name,
            channel_url=channel_url,
            summary=summary_ja,
        )

        log(f"Pipeline finished successfully for: {video_title}")

        return {
            "title": video_title,
            "transcript": txt_out,
            "summary_en": summary_en_path,
            "summary_ja": summary_ja_path,
            "summary_ja_text": summary_ja,
        }

    except subprocess.CalledProcessError as e:
        handle_error(f"Command failed: {e.cmd}", e)
    except Exception as e:
        handle_error("Pipeline execution failed", e)


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python -m clipmind.pipeline <YouTube URL>")
        sys.exit(1)
    run_pipeline(sys.argv[1])
