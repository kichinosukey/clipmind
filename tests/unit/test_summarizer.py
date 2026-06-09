"""Tests for clipmind.summarizer.summarize_text()."""

from dataclasses import replace

import pytest

from clipmind.summarizer import max_chunk_chars, summarize_text


class TestMaxChunkChars:
    def test_defaults_without_context_length(self):
        assert max_chunk_chars(None) == 8000

    def test_scales_with_context_length(self):
        assert max_chunk_chars(32768) > max_chunk_chars(4096)
        assert max_chunk_chars(4096) == 8384


class TestSummarizeText:
    @pytest.mark.parametrize("mode", ["summarize", "translate"])
    def test_returns_content(self, mode, llm_preset, mock_openai_client):
        assert summarize_text("Some text", mode=mode, preset=llm_preset) == (
            "Mocked summary output"
        )

    def test_empty_input_raises(self, llm_preset):
        with pytest.raises(ValueError, match="empty"):
            summarize_text("   ", mode="summarize", preset=llm_preset)

    def test_unsupported_mode_raises(self, llm_preset, mock_openai_client):
        with pytest.raises(ValueError, match="Unsupported"):
            summarize_text("Some text", mode="invalid", preset=llm_preset)

    def test_prompt_template_substitution(self, llm_preset, mock_openai_client):
        _, client = mock_openai_client
        summarize_text("MY_UNIQUE_TEXT", mode="summarize", preset=llm_preset)
        messages = client.chat.completions.create.call_args.kwargs["messages"]
        assert "MY_UNIQUE_TEXT" in messages[1]["content"]

    def test_template_fallback(self, llm_preset, mock_openai_client):
        preset = replace(llm_preset, summarize_user_prompt="Bad {unknown_key}")
        _, client = mock_openai_client
        summarize_text("fallback input", mode="summarize", preset=preset)
        messages = client.chat.completions.create.call_args.kwargs["messages"]
        assert "fallback input" in messages[1]["content"]

    def test_api_error_raises_original_exception(self, llm_preset, mock_openai_client):
        _, client = mock_openai_client
        client.chat.completions.create.side_effect = RuntimeError("API down")
        with pytest.raises(RuntimeError, match="API down"):
            summarize_text("Some text", mode="summarize", preset=llm_preset)

    def test_temperature_model_and_connection(self, llm_preset, mock_openai_client):
        _, client = mock_openai_client
        summarize_text("Some text", mode="summarize", preset=llm_preset)
        call = client.chat.completions.create.call_args
        assert call.kwargs["model"] == "test-model"
        assert call.kwargs["temperature"] == 0.3
