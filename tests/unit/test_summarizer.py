"""Tests for clipmind.summarizer.summarize_text()."""

import pytest


class TestSummarizeText:
    def test_summarize_returns_content(self, mocker, mock_openai_client):
        """mode='summarize' returns the LLM response content."""
        mocker.patch("clipmind.summarizer.MODEL", "test-model")
        mocker.patch("clipmind.summarizer.BASE_URL", "http://test:1234/v1")
        mocker.patch("clipmind.summarizer.API_KEY", "test-key")

        from clipmind.summarizer import summarize_text

        result = summarize_text("Some transcript text", mode="summarize")
        assert result == "Mocked summary output"

    def test_translate_returns_content(self, mocker, mock_openai_client):
        """mode='translate' returns the LLM response content."""
        mocker.patch("clipmind.summarizer.MODEL", "test-model")
        mocker.patch("clipmind.summarizer.BASE_URL", "http://test:1234/v1")
        mocker.patch("clipmind.summarizer.API_KEY", "test-key")

        from clipmind.summarizer import summarize_text

        result = summarize_text("Some summary text", mode="translate")
        assert result == "Mocked summary output"

    def test_empty_input_raises(self):
        """Empty string input raises ValueError."""
        from clipmind.summarizer import summarize_text

        with pytest.raises(ValueError, match="empty"):
            summarize_text("   ")

    def test_unsupported_mode_exits(self, mocker, mock_openai_client):
        """Unsupported mode raises SystemExit via handle_error."""
        mocker.patch("clipmind.summarizer.MODEL", "test-model")
        mocker.patch("clipmind.summarizer.BASE_URL", "http://test:1234/v1")
        mocker.patch("clipmind.summarizer.API_KEY", "test-key")

        from clipmind.summarizer import summarize_text

        with pytest.raises(SystemExit):
            summarize_text("Some text", mode="invalid_mode")

    def test_prompt_template_substitution(self, mocker, mock_openai_client):
        """{text} placeholder is replaced with actual input text."""
        mocker.patch("clipmind.summarizer.MODEL", "test-model")
        mocker.patch("clipmind.summarizer.BASE_URL", "http://test:1234/v1")
        mocker.patch("clipmind.summarizer.API_KEY", "test-key")

        from clipmind.summarizer import summarize_text

        _, mock_client = mock_openai_client
        summarize_text("MY_UNIQUE_TEXT", mode="summarize")

        call_args = mock_client.chat.completions.create.call_args
        messages = call_args.kwargs["messages"]
        user_msg = messages[1]["content"]
        assert "MY_UNIQUE_TEXT" in user_msg

    def test_template_fallback(self, mocker, mock_openai_client):
        """Malformed template falls back to appending text with \\n\\n."""
        mocker.patch("clipmind.summarizer.MODEL", "test-model")
        mocker.patch("clipmind.summarizer.BASE_URL", "http://test:1234/v1")
        mocker.patch("clipmind.summarizer.API_KEY", "test-key")
        # Use a template that will fail .format() — contains unmatched braces
        mocker.patch(
            "clipmind.summarizer.USER_PROMPTS",
            {"summarize": "Bad template {unknown_key}", "translate": "ok {text}"},
        )

        from clipmind.summarizer import summarize_text

        _, mock_client = mock_openai_client
        summarize_text("fallback input", mode="summarize")

        call_args = mock_client.chat.completions.create.call_args
        user_msg = call_args.kwargs["messages"][1]["content"]
        assert "fallback input" in user_msg

    def test_api_error_exits(self, mocker, mock_openai_client):
        """API exception causes SystemExit via handle_error."""
        mocker.patch("clipmind.summarizer.MODEL", "test-model")
        mocker.patch("clipmind.summarizer.BASE_URL", "http://test:1234/v1")
        mocker.patch("clipmind.summarizer.API_KEY", "test-key")

        _, mock_client = mock_openai_client
        mock_client.chat.completions.create.side_effect = RuntimeError("API down")

        from clipmind.summarizer import summarize_text

        with pytest.raises(SystemExit):
            summarize_text("Some text", mode="summarize")

    def test_temperature_and_model(self, mocker, mock_openai_client):
        """temperature=0.3 and MODEL are passed to the API call."""
        mocker.patch("clipmind.summarizer.MODEL", "test-model-123")
        mocker.patch("clipmind.summarizer.BASE_URL", "http://test:1234/v1")
        mocker.patch("clipmind.summarizer.API_KEY", "test-key")

        from clipmind.summarizer import summarize_text

        _, mock_client = mock_openai_client
        summarize_text("Some text", mode="summarize")

        call_args = mock_client.chat.completions.create.call_args
        assert call_args.kwargs["model"] == "test-model-123"
        assert call_args.kwargs["temperature"] == 0.3
