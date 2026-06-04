"""Shared test fixtures for clipmind test suite."""

import json
import os

import pytest

from clipmind.config import LLMPreset, RuntimeConfig


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


@pytest.fixture
def llm_preset():
    return LLMPreset(
        id="test",
        name="Test",
        base_url="http://test:1234/v1",
        model="test-model",
        api_key="test-key",
        summarize_system_prompt="summarize system",
        summarize_user_prompt="summarize {text}",
        translate_system_prompt="translate system",
        translate_user_prompt="translate {text}",
    )


@pytest.fixture
def runtime_config(llm_preset, tmp_path):
    return RuntimeConfig(
        preset=llm_preset,
        whisper_binary_path="/usr/bin/whisper-cli",
        whisper_model_path="/models/base.bin",
        output_root=str(tmp_path),
        default_destinations=("discord",),
        discord_webhook="https://discord.test/hook",
        slack_webhook=None,
    )


@pytest.fixture(autouse=True)
def shared_runtime_config(mocker, runtime_config):
    """Keep tests isolated from the user's real shared configuration."""
    mocker.patch("clipmind.config.load_runtime_config", return_value=runtime_config)
    mocker.patch("clipmind.pipeline.load_runtime_config", return_value=runtime_config)
