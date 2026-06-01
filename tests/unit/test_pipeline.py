"""Tests for clipmind.pipeline.run_pipeline()."""

import json
import os
import subprocess

import pytest


@pytest.fixture(autouse=True)
def _mute_ytdlp_startup_warn(mocker):
    mocker.patch("clipmind.pipeline.warn_if_outdated")


def _patch_subprocess_runs(mocker, side_effect):
    mocker.patch("clipmind.ytdlp_health.subprocess.run", side_effect=side_effect)
    mocker.patch("clipmind.pipeline.subprocess.run", side_effect=side_effect)


def _make_subprocess_side_effect(tmp_path, ytdlp_metadata, transcript_text="Hello world transcript."):
    """Create a side_effect function for subprocess.run that simulates yt-dlp and whisper."""
    safe_title = "".join(
        c if c.isalnum() or c in " _-" else "_" for c in ytdlp_metadata["title"]
    )[:80]
    channel = ytdlp_metadata["channel"]

    def side_effect(cmd, **kwargs):
        cmd_str = cmd[0] if cmd else ""
        if "yt-dlp" in cmd_str and "-J" in cmd:
            # yt-dlp metadata fetch
            mock_result = subprocess.CompletedProcess(
                cmd, 0, stdout=json.dumps(ytdlp_metadata), stderr=""
            )
            return mock_result
        elif "yt-dlp" in cmd_str and "--no-playlist" in cmd:
            # yt-dlp audio download — create the WAV file
            outdir = os.path.join(str(tmp_path), channel, safe_title)
            os.makedirs(outdir, exist_ok=True)
            wav_path = os.path.join(outdir, f"{safe_title}.wav")
            with open(wav_path, "wb") as f:
                f.write(b"RIFF" + b"\x00" * 100)
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
        elif "whisper" in cmd_str:
            # whisper-cli — create the TXT file
            # The -of flag value is the output path without extension
            of_idx = cmd.index("-of") if "-of" in cmd else None
            if of_idx is not None:
                txt_path = cmd[of_idx + 1] + ".txt"
            else:
                txt_path = os.path.join(str(tmp_path), channel, safe_title, f"{safe_title}.txt")
            os.makedirs(os.path.dirname(txt_path), exist_ok=True)
            with open(txt_path, "w") as f:
                f.write(transcript_text)
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    return side_effect


class TestRunPipeline:
    def test_happy_path(self, mocker, tmp_path, ytdlp_metadata):
        """Full pipeline returns dict with expected keys."""
        mocker.patch("clipmind.pipeline.os.getenv", side_effect=lambda k, d="": {
            "SKIP_WAV_DOWNLOAD": "0",
            "SKIP_TRANSCRIBE": "0",
            "DISCORD_WEBHOOK_URL": "",
        }.get(k, d))
        mock_sub = _patch_subprocess_runs(
            mocker,
            _make_subprocess_side_effect(tmp_path, ytdlp_metadata),
        )
        mocker.patch("clipmind.pipeline.summarize_text", side_effect=["English summary", "日本語要約"])
        mocker.patch("clipmind.pipeline.resolve_destination", return_value=mocker.MagicMock())

        from clipmind.pipeline import run_pipeline

        result = run_pipeline("https://youtu.be/test", outroot=str(tmp_path))
        assert "title" in result
        assert "transcript" in result
        assert "summary_en" in result
        assert "summary_ja" in result
        assert "summary_text" in result
        assert "summary_ja_text" in result

    def test_creates_output_dirs(self, mocker, tmp_path, ytdlp_metadata):
        """Output directory is created."""
        mocker.patch("clipmind.pipeline.os.getenv", side_effect=lambda k, d="": {
            "SKIP_WAV_DOWNLOAD": "0",
            "SKIP_TRANSCRIBE": "0",
            "DISCORD_WEBHOOK_URL": "",
        }.get(k, d))
        _patch_subprocess_runs(
            mocker,
            _make_subprocess_side_effect(tmp_path, ytdlp_metadata),
        )
        mocker.patch("clipmind.pipeline.summarize_text", side_effect=["en", "ja"])
        mocker.patch("clipmind.pipeline.resolve_destination", return_value=mocker.MagicMock())

        from clipmind.pipeline import run_pipeline

        run_pipeline("https://youtu.be/test", outroot=str(tmp_path))
        outdir = os.path.join(str(tmp_path), "TestChannel", "Test Video Title")
        assert os.path.isdir(outdir)

    def test_writes_metadata_json(self, mocker, tmp_path, ytdlp_metadata):
        """metadata.json is written with expected fields."""
        mocker.patch("clipmind.pipeline.os.getenv", side_effect=lambda k, d="": {
            "SKIP_WAV_DOWNLOAD": "0",
            "SKIP_TRANSCRIBE": "0",
            "DISCORD_WEBHOOK_URL": "",
        }.get(k, d))
        _patch_subprocess_runs(
            mocker,
            _make_subprocess_side_effect(tmp_path, ytdlp_metadata),
        )
        mocker.patch("clipmind.pipeline.summarize_text", side_effect=["en summary", "ja summary"])
        mocker.patch("clipmind.pipeline.resolve_destination", return_value=mocker.MagicMock())

        from clipmind.pipeline import run_pipeline

        run_pipeline("https://youtu.be/test", outroot=str(tmp_path))

        meta_path = os.path.join(str(tmp_path), "TestChannel", "Test Video Title", "metadata.json")
        assert os.path.exists(meta_path)
        with open(meta_path) as f:
            meta = json.load(f)
        assert meta["title"] == "Test Video Title"
        assert meta["channel"] == "TestChannel"
        assert "summary_en_len" in meta
        assert "summary_ja_len" in meta

    def test_writes_summary_files(self, mocker, tmp_path, ytdlp_metadata):
        """_summary.txt and _summary_ja.txt are written."""
        mocker.patch("clipmind.pipeline.os.getenv", side_effect=lambda k, d="": {
            "SKIP_WAV_DOWNLOAD": "0",
            "SKIP_TRANSCRIBE": "0",
            "DISCORD_WEBHOOK_URL": "",
        }.get(k, d))
        _patch_subprocess_runs(
            mocker,
            _make_subprocess_side_effect(tmp_path, ytdlp_metadata),
        )
        mocker.patch("clipmind.pipeline.summarize_text", side_effect=["English text", "Japanese text"])
        mocker.patch("clipmind.pipeline.resolve_destination", return_value=mocker.MagicMock())

        from clipmind.pipeline import run_pipeline

        result = run_pipeline("https://youtu.be/test", outroot=str(tmp_path))
        assert os.path.exists(result["summary_en"])
        assert os.path.exists(result["summary_ja"])
        with open(result["summary_en"]) as f:
            assert f.read() == "English text"
        with open(result["summary_ja"]) as f:
            assert f.read() == "Japanese text"

    def test_skip_wav_download(self, mocker, tmp_path, ytdlp_metadata):
        """skip_wav_download=True + WAV exists → download is skipped."""
        mocker.patch("clipmind.pipeline.os.getenv", side_effect=lambda k, d="": {
            "SKIP_WAV_DOWNLOAD": "0",
            "SKIP_TRANSCRIBE": "0",
            "DISCORD_WEBHOOK_URL": "",
        }.get(k, d))

        # Pre-create the WAV file
        safe_title = "Test Video Title"
        outdir = os.path.join(str(tmp_path), "TestChannel", safe_title)
        os.makedirs(outdir, exist_ok=True)
        wav_path = os.path.join(outdir, f"{safe_title}.wav")
        with open(wav_path, "wb") as f:
            f.write(b"RIFF" + b"\x00" * 100)

        call_log = []

        def tracking_side_effect(cmd, **kwargs):
            call_log.append(cmd)
            cmd_str = cmd[0] if cmd else ""
            if "yt-dlp" in cmd_str and "-J" in cmd:
                return subprocess.CompletedProcess(
                    cmd, 0, stdout=json.dumps(ytdlp_metadata), stderr=""
                )
            elif "whisper" in cmd_str:
                txt_path = wav_path.replace(".wav", ".txt")
                with open(txt_path, "w") as f:
                    f.write("transcript text")
                return subprocess.CompletedProcess(cmd, 0)
            return subprocess.CompletedProcess(cmd, 0)

        _patch_subprocess_runs(mocker, tracking_side_effect)
        mocker.patch("clipmind.pipeline.summarize_text", side_effect=["en", "ja"])
        mocker.patch("clipmind.pipeline.resolve_destination", return_value=mocker.MagicMock())

        from clipmind.pipeline import run_pipeline

        run_pipeline("https://youtu.be/test", outroot=str(tmp_path), skip_wav_download=True)

        # Verify yt-dlp --no-playlist was NOT called
        download_calls = [c for c in call_log if "--no-playlist" in c]
        assert len(download_calls) == 0

    def test_skip_transcribe(self, mocker, tmp_path, ytdlp_metadata):
        """skip_transcribe=True + TXT exists → Whisper is skipped."""
        mocker.patch("clipmind.pipeline.os.getenv", side_effect=lambda k, d="": {
            "SKIP_WAV_DOWNLOAD": "0",
            "SKIP_TRANSCRIBE": "0",
            "DISCORD_WEBHOOK_URL": "",
        }.get(k, d))

        safe_title = "Test Video Title"
        outdir = os.path.join(str(tmp_path), "TestChannel", safe_title)
        os.makedirs(outdir, exist_ok=True)
        wav_path = os.path.join(outdir, f"{safe_title}.wav")
        txt_path = os.path.join(outdir, f"{safe_title}.txt")
        with open(wav_path, "wb") as f:
            f.write(b"RIFF")
        with open(txt_path, "w") as f:
            f.write("pre-existing transcript")

        call_log = []

        def tracking_side_effect(cmd, **kwargs):
            call_log.append(cmd)
            cmd_str = cmd[0] if cmd else ""
            if "yt-dlp" in cmd_str and "-J" in cmd:
                return subprocess.CompletedProcess(
                    cmd, 0, stdout=json.dumps(ytdlp_metadata), stderr=""
                )
            elif "yt-dlp" in cmd_str:
                return subprocess.CompletedProcess(cmd, 0)
            return subprocess.CompletedProcess(cmd, 0)

        _patch_subprocess_runs(mocker, tracking_side_effect)
        mocker.patch("clipmind.pipeline.summarize_text", side_effect=["en", "ja"])
        mocker.patch("clipmind.pipeline.resolve_destination", return_value=mocker.MagicMock())

        from clipmind.pipeline import run_pipeline

        run_pipeline(
            "https://youtu.be/test",
            outroot=str(tmp_path),
            skip_wav_download=True,
            skip_transcribe=True,
        )

        whisper_calls = [c for c in call_log if any("whisper" in str(arg) for arg in c)]
        assert len(whisper_calls) == 0

    def test_skip_flags_from_env(self, mocker, tmp_path, ytdlp_metadata):
        """env SKIP_WAV_DOWNLOAD=1 is respected."""
        safe_title = "Test Video Title"
        outdir = os.path.join(str(tmp_path), "TestChannel", safe_title)
        os.makedirs(outdir, exist_ok=True)
        wav_path = os.path.join(outdir, f"{safe_title}.wav")
        with open(wav_path, "wb") as f:
            f.write(b"RIFF")

        env_map = {
            "SKIP_WAV_DOWNLOAD": "1",
            "SKIP_TRANSCRIBE": "0",
            "DISCORD_WEBHOOK_URL": "",
        }
        mocker.patch("clipmind.pipeline.os.getenv", side_effect=lambda k, d="": env_map.get(k, d))

        call_log = []

        def tracking_side_effect(cmd, **kwargs):
            call_log.append(cmd)
            cmd_str = cmd[0] if cmd else ""
            if "yt-dlp" in cmd_str and "-J" in cmd:
                return subprocess.CompletedProcess(
                    cmd, 0, stdout=json.dumps(ytdlp_metadata), stderr=""
                )
            elif "whisper" in cmd_str:
                txt_path = wav_path.replace(".wav", ".txt")
                with open(txt_path, "w") as f:
                    f.write("transcript text")
                return subprocess.CompletedProcess(cmd, 0)
            return subprocess.CompletedProcess(cmd, 0)

        _patch_subprocess_runs(mocker, tracking_side_effect)
        mocker.patch("clipmind.pipeline.summarize_text", side_effect=["en", "ja"])
        mocker.patch("clipmind.pipeline.resolve_destination", return_value=mocker.MagicMock())

        from clipmind.pipeline import run_pipeline

        run_pipeline("https://youtu.be/test", outroot=str(tmp_path))

        download_calls = [c for c in call_log if "--no-playlist" in c]
        assert len(download_calls) == 0

    def test_no_destinations_uses_default(self, mocker, tmp_path, ytdlp_metadata):
        """No destinations arg → defaults to ["discord"]."""
        mocker.patch("clipmind.pipeline.os.getenv", side_effect=lambda k, d="": {
            "SKIP_WAV_DOWNLOAD": "0",
            "SKIP_TRANSCRIBE": "0",
        }.get(k, d))
        _patch_subprocess_runs(
            mocker,
            _make_subprocess_side_effect(tmp_path, ytdlp_metadata),
        )
        mocker.patch("clipmind.pipeline.summarize_text", side_effect=["en", "ja"])
        mock_resolve = mocker.patch("clipmind.pipeline.resolve_destination", return_value=mocker.MagicMock())

        from clipmind.pipeline import run_pipeline

        result = run_pipeline("https://youtu.be/test", outroot=str(tmp_path))
        mock_resolve.assert_called_once_with("discord")
        assert "delivery_results" in result

    def test_subprocess_failure_exits(self, mocker, tmp_path):
        """yt-dlp CalledProcessError → SystemExit."""
        mocker.patch("clipmind.pipeline.os.getenv", side_effect=lambda k, d="": {
            "SKIP_WAV_DOWNLOAD": "0",
            "SKIP_TRANSCRIBE": "0",
            "DISCORD_WEBHOOK_URL": "",
        }.get(k, d))
        _patch_subprocess_runs(
            mocker,
            side_effect=subprocess.CalledProcessError(1, ["yt-dlp", "-J"]),
        )

        from clipmind.pipeline import run_pipeline

        with pytest.raises(SystemExit):
            run_pipeline("https://youtu.be/test", outroot=str(tmp_path))

    def test_safe_title_sanitization(self, mocker, tmp_path):
        """Special characters are replaced with '_', limited to 80 chars."""
        metadata = {
            "title": "Title/With:Special|Chars!" + "A" * 100,
            "channel": "Ch",
            "channel_url": "https://youtube.com/@Ch",
        }
        mocker.patch("clipmind.pipeline.os.getenv", side_effect=lambda k, d="": {
            "SKIP_WAV_DOWNLOAD": "0",
            "SKIP_TRANSCRIBE": "0",
            "DISCORD_WEBHOOK_URL": "",
        }.get(k, d))
        mocker.patch(
            "clipmind.pipeline.subprocess.run",
            side_effect=_make_subprocess_side_effect(tmp_path, metadata),
        )
        mocker.patch("clipmind.pipeline.summarize_text", side_effect=["en", "ja"])
        mocker.patch("clipmind.pipeline.resolve_destination", return_value=mocker.MagicMock())

        from clipmind.pipeline import run_pipeline

        result = run_pipeline("https://youtu.be/test", outroot=str(tmp_path))
        # The safe_title directory should exist and have no special chars
        title_dir = os.path.basename(os.path.dirname(result["transcript"]))
        assert "/" not in title_dir
        assert ":" not in title_dir
        assert "|" not in title_dir
        assert len(title_dir) <= 80

    def test_empty_transcript_exits(self, mocker, tmp_path, ytdlp_metadata):
        """Empty transcription file → SystemExit."""
        mocker.patch("clipmind.pipeline.os.getenv", side_effect=lambda k, d="": {
            "SKIP_WAV_DOWNLOAD": "0",
            "SKIP_TRANSCRIBE": "0",
            "DISCORD_WEBHOOK_URL": "",
        }.get(k, d))
        mocker.patch(
            "clipmind.pipeline.subprocess.run",
            side_effect=_make_subprocess_side_effect(
                tmp_path, ytdlp_metadata, transcript_text=""
            ),
        )
        mocker.patch("clipmind.pipeline.summarize_text", side_effect=["en", "ja"])
        mocker.patch("clipmind.pipeline.resolve_destination", return_value=mocker.MagicMock())

        from clipmind.pipeline import run_pipeline

        with pytest.raises(SystemExit):
            run_pipeline("https://youtu.be/test", outroot=str(tmp_path))
