"""Integration tests — pipeline + summarizer + discord_client with only external boundaries mocked."""

import json
import os
import subprocess

import pytest
import responses


WEBHOOK_URL = "https://discord.com/api/webhooks/test/integration"


def _make_subprocess_side_effect(tmp_path, title="Integration Test Video", channel="IntegrationCh"):
    """Create subprocess.run side_effect for integration tests."""
    safe_title = "".join(c if c.isalnum() or c in " _-" else "_" for c in title)[:80]

    metadata = {
        "title": title,
        "channel": channel,
        "channel_url": f"https://www.youtube.com/@{channel}",
    }

    def side_effect(cmd, **kwargs):
        cmd_str = cmd[0] if cmd else ""
        if "yt-dlp" in cmd_str and "-J" in cmd:
            return subprocess.CompletedProcess(
                cmd, 0, stdout=json.dumps(metadata), stderr=""
            )
        elif "yt-dlp" in cmd_str and "--no-playlist" in cmd:
            outdir = os.path.join(str(tmp_path), channel, safe_title)
            os.makedirs(outdir, exist_ok=True)
            wav_path = os.path.join(outdir, f"{safe_title}.wav")
            with open(wav_path, "wb") as f:
                f.write(b"RIFF" + b"\x00" * 100)
            return subprocess.CompletedProcess(cmd, 0)
        elif "whisper" in cmd_str:
            of_idx = cmd.index("-of") if "-of" in cmd else None
            if of_idx is not None:
                txt_path = cmd[of_idx + 1] + ".txt"
            else:
                txt_path = os.path.join(str(tmp_path), channel, safe_title, f"{safe_title}.txt")
            os.makedirs(os.path.dirname(txt_path), exist_ok=True)
            with open(txt_path, "w") as f:
                f.write(
                    "Today we discuss the future of AI and its implications. "
                    "Machine learning is transforming many industries."
                )
            return subprocess.CompletedProcess(cmd, 0)
        return subprocess.CompletedProcess(cmd, 0)

    return side_effect


class TestFullPipelineIntegration:
    @responses.activate
    def test_full_pipeline_with_discord(self, mocker, tmp_path):
        """URL → summarize → translate → Discord post, all output files verified."""
        # Mock only external boundaries: subprocess, OpenAI, HTTP
        mocker.patch(
            "clipmind.pipeline.subprocess.run",
            side_effect=_make_subprocess_side_effect(tmp_path),
        )

        # Mock OpenAI at the summarizer level
        mock_choice = mocker.MagicMock()
        mock_response = mocker.MagicMock()
        mock_response.choices = [mock_choice]
        mock_client = mocker.MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mocker.patch("clipmind.summarizer.OpenAI", return_value=mock_client)

        # Different responses for summarize vs translate
        call_count = [0]

        def mock_create(**kwargs):
            call_count[0] += 1
            mock_c = mocker.MagicMock()
            if call_count[0] == 1:
                mock_c.message.content = "Topic: AI Future\nKey Points:\n- AI is transforming industries"
            else:
                mock_c.message.content = "トピック: AIの未来\n要点:\n- AIは産業を変革している"
            mock_r = mocker.MagicMock()
            mock_r.choices = [mock_c]
            return mock_r

        mock_client.chat.completions.create.side_effect = mock_create

        # Mock Discord webhook — also patch DEFAULT_WEBHOOK_URL in discord_client
        # so post_to_discord uses the test URL when called without explicit webhook_url
        responses.add(responses.POST, WEBHOOK_URL, status=200)
        from clipmind.pipeline import run_pipeline

        result = run_pipeline("https://youtu.be/integration", outroot=str(tmp_path))

        # Verify return value
        assert result["title"] == "Integration Test Video"
        assert os.path.exists(result["summary_en"])
        assert os.path.exists(result["summary_ja"])
        assert os.path.exists(result["transcript"])

        # Verify summary content
        with open(result["summary_en"]) as f:
            assert "AI" in f.read()
        with open(result["summary_ja"]) as f:
            assert "AI" in f.read()

        # Verify metadata.json
        outdir = os.path.dirname(result["transcript"])
        with open(os.path.join(outdir, "metadata.json")) as f:
            meta = json.load(f)
        assert meta["title"] == "Integration Test Video"
        assert meta["channel"] == "IntegrationCh"

        # Verify Discord was called
        assert len(responses.calls) >= 1

    @responses.activate
    def test_full_pipeline_without_discord(self, mocker, tmp_path):
        """Discord disabled (no webhook URL) → no HTTP calls made."""
        mocker.patch(
            "clipmind.pipeline.subprocess.run",
            side_effect=_make_subprocess_side_effect(tmp_path),
        )

        mock_choice = mocker.MagicMock()
        mock_choice.message.content = "Summary content"
        mock_response = mocker.MagicMock()
        mock_response.choices = [mock_choice]
        mock_client = mocker.MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mocker.patch("clipmind.summarizer.OpenAI", return_value=mock_client)
        from clipmind.pipeline import run_pipeline

        result = run_pipeline(
            "https://youtu.be/no-discord", outroot=str(tmp_path), destinations=[]
        )

        assert result["title"] == "Integration Test Video"
        # No HTTP calls should have been made (Discord skipped due to no webhook)
        assert len(responses.calls) == 0
