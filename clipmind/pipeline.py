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

import json
import os
import subprocess
import uuid
import argparse
import sys
from pathlib import Path
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode

from clipmind.clip import Clip
from clipmind.config import RuntimeConfig, load_runtime_config
from clipmind.jobs import JobStage, JobStatusStore
from clipmind.paths import JOBS_DIR
from clipmind.secrets import redact_secrets
from clipmind.summarizer import summarize_text
from clipmind.destinations import resolve_destination
from clipmind.utils.log import log
from clipmind.ytdlp_health import run_ytdlp_with_fallback, warn_if_outdated

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
    *,
    config: RuntimeConfig | None = None,
    reporter: JobStatusStore | None = None,
    destinations: list[str] | None = None,
    outroot: str | None = None,
    skip_wav_download: bool = False,
    skip_transcribe: bool = False,
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
    config = config or load_runtime_config()
    destinations = destinations if destinations is not None else list(config.default_destinations)

    url = _normalize_youtube_url(url)

    try:
        # ==== 出力先の決定 ====
        outroot = outroot or config.output_root
        outroot = str(Path(outroot).expanduser())
        Path(outroot).mkdir(parents=True, exist_ok=True)
        log(f"Output root directory: {outroot}")

        # ==== Whisper設定 ====
        whisper_bin = str(Path(config.whisper_binary_path).expanduser())
        whisper_model = str(Path(config.whisper_model_path).expanduser())
        log(f"Using Whisper binary: {whisper_bin}")
        log(f"Using Whisper model: {whisper_model}")

        log(f"Pipeline started for: {url}")
        log(f"Destinations: {destinations}")

        warn_if_outdated()

        # ==== 1. 動画メタデータ取得 ====
        if reporter:
            reporter.transition(JobStage.DOWNLOADING_AUDIO)
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
        if reporter:
            reporter.set_title(video_title)

        # ==== 2. ダウンロードディレクトリ設定 ====
        safe_title = "".join(c if c.isalnum() or c in " _-" else "_" for c in video_title)[:80]
        outdir = str(Path(outroot) / channel_name / safe_title)
        Path(outdir).mkdir(parents=True, exist_ok=True)
        wav_path = str(Path(outdir) / f"{safe_title}.wav")

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
        if reporter:
            reporter.transition(JobStage.TRANSCRIBING_WITH_WHISPER)
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
        if reporter:
            reporter.transition(JobStage.SUMMARIZING)
        log("Summarizing in English...")
        summary_en = summarize_text(
            text,
            "summarize",
            config.preset,
            context_length=config.context_length,
        )
        log(f"DEBUG: summary_en length = {len(summary_en)}")

        summary_en_path = txt_out.replace(".txt", "_summary.txt")
        with open(summary_en_path, "w", encoding="utf-8") as f:
            f.write(summary_en)
        log(f"English summary written to: {summary_en_path}")

        clip.summary_en = summary_en

        # ==== 6. 翻訳 ====
        if reporter:
            reporter.transition(JobStage.TRANSLATING)
        log("Translating to Japanese...")
        summary_ja = summarize_text(
            summary_en,
            "translate",
            config.preset,
            context_length=config.context_length,
        )
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
        if reporter:
            reporter.transition(JobStage.DELIVERING)
        delivery_results: dict[str, str] = {}
        for dest_name in destinations:
            try:
                webhook_url = (
                    config.discord_webhook
                    if dest_name == "discord"
                    else config.slack_webhook if dest_name == "slack" else None
                )
                dest = resolve_destination(dest_name, webhook_url=webhook_url)
                dest.post(clip)
                delivery_results[dest_name] = "ok"
                log(f"Posted to {dest_name} successfully")
            except Exception as e:
                error = redact_secrets(str(e), config.secrets)
                log(f"Failed to post to {dest_name}: {error}", "ERROR")
                delivery_results[dest_name] = f"error: {error}"

        clip.metadata["delivery_results"] = delivery_results

        log(f"Pipeline finished for: {video_title} (delivery: {delivery_results})")
        if reporter:
            reporter.complete(delivery_results)

        return {
            "title": video_title,
            "transcript": txt_out,
            "summary_en": summary_en_path,
            "summary_ja": summary_ja_path,
            "summary_ja_text": summary_ja,
            "summary_text": summary_en,
            "delivery_results": delivery_results,
        }

    except Exception as e:
        if reporter:
            reporter.fail(e)
        raise


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python -m clipmind.pipeline <YouTube URL> [destinations]")
        return 1
    parser = argparse.ArgumentParser(description="Run the ClipMind YouTube pipeline")
    parser.add_argument("url")
    parser.add_argument("destinations", nargs="?")
    args = parser.parse_args()
    try:
        config = load_runtime_config()
        reporter = JobStatusStore(
            JOBS_DIR,
            job_id=uuid.uuid4().hex[:12],
            source_url=args.url,
            secrets=config.secrets,
        )
        run_pipeline(
            args.url,
            config=config,
            reporter=reporter,
            destinations=args.destinations.split(",") if args.destinations else None,
        )
        return 0
    except Exception as exc:
        secrets = config.secrets if "config" in locals() else []
        log(redact_secrets(str(exc), secrets), "ERROR")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
