#!/usr/bin/env python3
"""
clipmind.pipeline
----------------

YouTube動画URLを起点に、以下の一連の処理を自動実行する統合パイプライン。

1. YouTubeから音声をダウンロード（yt-dlp）
2. Whisper.cppによる文字起こし
3. LLMによる要約（英語）
4. LLMによる日本語翻訳
5. 指定されたデスティネーションへの投稿（Discord / Slack）

想定用途:
- Alfred Workflow からの呼び出し
- RSS / cron / Webhook などの自動トリガー
- CLIスクリプトや他ツールからの直接呼び出し
- Chrome拡張からのNative Messaging経由呼び出し
"""

from __future__ import annotations

import os
import json
import subprocess
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode

from clipmind.clip import Clip
from clipmind.summarizer import summarize_text
from clipmind.destinations import resolve_destination
from clipmind.paths import (
    DEFAULT_OUTROOT,
    DEFAULT_WHISPER_BIN,
    DEFAULT_WHISPER_MODEL,
    load_project_dotenv,
)
from clipmind.utils.log import log
from clipmind.utils.error import handle_error
from clipmind.ytdlp_health import run_ytdlp_with_fallback, warn_if_outdated

# ==== .env 読み込み ====
load_project_dotenv()


_YT_HOSTS = {"www.youtube.com", "youtube.com", "m.youtube.com", "music.youtube.com"}
_YT_STRIP_PARAMS = {"list", "index", "start_radio", "pp", "si", "feature"}


def _normalize_youtube_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.hostname not in _YT_HOSTS:
        return url
    kept = [(k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=True)
            if k not in _YT_STRIP_PARAMS]
    return urlunparse(parsed._replace(query=urlencode(kept)))


def run_pipeline(
    url: str,
    destinations: list[str] | None = None,
    outroot: str | None = None,
    whisper_bin: str | None = None,
    whisper_model: str | None = None,
    skip_wav_download: bool | None = None,
    skip_transcribe: bool | None = None,
) -> dict:
    """YouTube URLを入力として、要約〜投稿までを自動実行する。

    Args:
        url: 対象のYouTube動画URL。
        destinations: 投稿先リスト（例: ["discord", "slack"]）。未指定なら ["discord"]。
        outroot: 出力ルートディレクトリ。
        whisper_bin: whisper-cli の実行パス。
        whisper_model: Whisperモデルファイルのパス。

    Returns:
        dict: 実行結果情報を含む辞書。
    """
    if destinations is None:
        destinations = ["discord"]

    url = _normalize_youtube_url(url)

    try:
        # ==== フラグの決定 ====
        skip_wav_download = (
            skip_wav_download
            if skip_wav_download is not None
            else bool(int(os.getenv("SKIP_WAV_DOWNLOAD", "0")))
        )
        skip_transcribe = (
            skip_transcribe
            if skip_transcribe is not None
            else bool(int(os.getenv("SKIP_TRANSCRIBE", "0")))
        )

        # ==== 出力先の決定 ====
        outroot = outroot or os.getenv("OUTROOT", DEFAULT_OUTROOT)
        outroot = os.path.expanduser(outroot)
        os.makedirs(outroot, exist_ok=True)
        log(f"Output root directory: {outroot}")

        # ==== Whisper設定 ====
        whisper_bin = whisper_bin or os.getenv("WHISPER_BIN", DEFAULT_WHISPER_BIN)
        whisper_model = whisper_model or os.getenv("WHISPER_MODEL", DEFAULT_WHISPER_MODEL)
        whisper_bin = os.path.expanduser(whisper_bin)
        whisper_model = os.path.expanduser(whisper_model)
        log(f"Using Whisper binary: {whisper_bin}")
        log(f"Using Whisper model: {whisper_model}")

        log(f"Pipeline started for: {url}")
        log(f"Destinations: {destinations}")

        warn_if_outdated()

        # ==== 1. 動画メタデータ取得 ====
        log("Fetching video metadata...")
        result = run_ytdlp_with_fallback(
            ["-J", url],
            capture_output=True,
            text=True,
            check=True,
        )
        info = json.loads(result.stdout)

        video_title = info.get("title", "unknown_title")
        channel_name = info.get("channel", "unknown_channel")
        channel_url = info.get("channel_url", "")

        # ==== Clipオブジェクト生成 ====
        clip = Clip(
            source_type="youtube",
            url=url,
            title=video_title,
            author=channel_name,
            author_url=channel_url,
        )

        # ==== 2. ダウンロードディレクトリ設定 ====
        safe_title = "".join(c if c.isalnum() or c in " _-" else "_" for c in video_title)[:80]
        outdir = os.path.join(outroot, channel_name, safe_title)
        os.makedirs(outdir, exist_ok=True)
        wav_path = os.path.join(outdir, f"{safe_title}.wav")

        # ==== 3. 音声ダウンロード ====
        if skip_wav_download and os.path.exists(wav_path):
            log(f"Skip wav download (exists): {wav_path}")
        else:
            log(f"Downloading audio to {wav_path} ...")
            run_ytdlp_with_fallback(
                [
                    "--no-playlist", "-f", "bestaudio", "-x",
                    "--audio-format", "wav", "-o", wav_path, url,
                ],
                check=True,
            )

        if not os.path.exists(wav_path):
            raise FileNotFoundError(f"Audio file not found after download/skip: {wav_path}")

        clip.audio_path = wav_path

        # ==== 4. Whisper文字起こし ====
        txt_out = wav_path.replace(".wav", ".txt")
        if skip_transcribe and os.path.exists(txt_out):
            log(f"Skip transcription (exists): {txt_out}")
        else:
            log("Transcribing with Whisper...")
            subprocess.run([
                whisper_bin, "-m", whisper_model, "-f", wav_path,
                "-otxt", "-of", txt_out[:-4]
            ], check=True)

        if not os.path.exists(txt_out):
            raise FileNotFoundError(f"Transcription output not found after run/skip: {txt_out}")

        with open(txt_out, "r", encoding="utf-8") as f:
            text = f.read()
        if not text.strip():
            raise ValueError("Transcription file is empty.")

        clip.transcript = text

        # ==== 5. 要約 ====
        log("Summarizing in English...")
        summary_en = summarize_text(text, "summarize")
        log(f"DEBUG: summary_en length = {len(summary_en)}")

        summary_en_path = txt_out.replace(".txt", "_summary.txt")
        with open(summary_en_path, "w", encoding="utf-8") as f:
            f.write(summary_en)
        log(f"English summary written to: {summary_en_path}")

        clip.summary_en = summary_en

        # ==== 6. 翻訳 ====
        log("Translating to Japanese...")
        summary_ja = summarize_text(summary_en, "translate")
        log(f"DEBUG: summary_ja length = {len(summary_ja)}")

        summary_ja_path = txt_out.replace(".txt", "_summary_ja.txt")
        with open(summary_ja_path, "w", encoding="utf-8") as f:
            f.write(summary_ja)
        log(f"Japanese summary written to: {summary_ja_path}")

        clip.summary_ja = summary_ja

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

        # ==== 8. デスティネーションへ投稿（per-destination error isolation） ====
        delivery_results: dict[str, str] = {}
        for dest_name in destinations:
            try:
                dest = resolve_destination(dest_name)
                dest.post(clip)
                delivery_results[dest_name] = "ok"
                log(f"Posted to {dest_name} successfully")
            except Exception as e:
                log(f"Failed to post to {dest_name}: {e}", "ERROR")
                delivery_results[dest_name] = f"error: {e}"

        clip.metadata["delivery_results"] = delivery_results

        log(f"Pipeline finished for: {video_title} (delivery: {delivery_results})")

        return {
            "title": video_title,
            "transcript": txt_out,
            "summary_en": summary_en_path,
            "summary_ja": summary_ja_path,
            "summary_ja_text": summary_ja,
            "summary_text": summary_en,
            "delivery_results": delivery_results,
        }

    except subprocess.CalledProcessError as e:
        handle_error(f"Command failed: {e.cmd}", e)
    except Exception as e:
        handle_error("Pipeline execution failed", e)


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python -m clipmind.pipeline <YouTube URL> [destinations]")
        print("  destinations: comma-separated list (e.g., discord,slack)")
        sys.exit(1)
    dests = sys.argv[2].split(",") if len(sys.argv) > 2 else None
    run_pipeline(sys.argv[1], destinations=dests)
