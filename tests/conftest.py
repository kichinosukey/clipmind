"""Shared test fixtures for clipmind test suite."""

import json
import os

import pytest


@pytest.fixture
def mock_env(monkeypatch):
    """Minimal environment variables for clipmind modules."""
    env = {
        "BASE_URL": "http://test-llm:1234/v1",
        "API_KEY": "test-key",
        "MODEL": "test-model",
        "DISCORD_WEBHOOK_URL": "https://discord.com/api/webhooks/test/token",
        "OUTROOT": "",  # will be overridden per-test with tmp_path
        "SKIP_WAV_DOWNLOAD": "0",
        "SKIP_TRANSCRIBE": "0",
    }
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    return env


@pytest.fixture
def ytdlp_metadata():
    """Sample yt-dlp -J return value."""
    return {
        "title": "Test Video Title",
        "channel": "TestChannel",
        "channel_url": "https://www.youtube.com/@TestChannel",
    }


@pytest.fixture
def fake_transcript(tmp_path):
    """Create a temporary transcript file and return its path."""
    txt = tmp_path / "transcript.txt"
    txt.write_text(
        "Hello everyone. Today we are going to discuss AI safety. "
        "It is a very important topic that we need to address carefully.",
        encoding="utf-8",
    )
    return txt


@pytest.fixture
def mock_openai_client(mocker):
    """Mock clipmind.summarizer.OpenAI and return a fixed response."""
    mock_choice = mocker.MagicMock()
    mock_choice.message.content = "Mocked summary output"

    mock_response = mocker.MagicMock()
    mock_response.choices = [mock_choice]

    mock_client = mocker.MagicMock()
    mock_client.chat.completions.create.return_value = mock_response

    mock_cls = mocker.patch("clipmind.summarizer.OpenAI", return_value=mock_client)
    return mock_cls, mock_client
