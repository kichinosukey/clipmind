"""
ELI10要約プロンプトの構造テスト。
プロンプト本文の意味的品質はLLM出力でしか検証できないので、
ここでは「フォーマットの骨格」と「ELI10指示が含まれていること」
だけを構造的に保証する。意味的検証は1週間の手動評価で行う。
"""
from clipmind.summarizer import (
    DEFAULT_SYSTEM_SUMMARIZE_PROMPT,
    DEFAULT_USER_SUMMARIZE_PROMPT,
)


class TestEli10SystemPrompt:
    def test_system_prompt_signals_plain_language(self):
        prompt = DEFAULT_SYSTEM_SUMMARIZE_PROMPT.lower()
        assert "expert assistant" not in prompt
        plain_signals = ["plain", "everyday", "simple", "friend", "10-year-old", "kid"]
        assert any(s in prompt for s in plain_signals), (
            f"system prompt must signal plain-language style, got: {prompt!r}"
        )

    def test_system_prompt_keeps_accuracy_constraint(self):
        prompt = DEFAULT_SYSTEM_SUMMARIZE_PROMPT.lower()
        assert "not in the transcript" in prompt or "do not add" in prompt or "don't add" in prompt


class TestEli10UserPrompt:
    def test_user_prompt_uses_new_section_headers(self):
        prompt = DEFAULT_USER_SUMMARIZE_PROMPT
        assert "What it's about:" in prompt
        assert "What they're saying:" in prompt
        assert "Notable Quotes:" in prompt
        assert "So what?:" in prompt

    def test_user_prompt_drops_old_section_headers(self):
        prompt = DEFAULT_USER_SUMMARIZE_PROMPT
        assert "Topic:" not in prompt
        assert "Key Points:" not in prompt
        assert "Conclusion:" not in prompt

    def test_user_prompt_keeps_text_placeholder(self):
        assert "{text}" in DEFAULT_USER_SUMMARIZE_PROMPT

    def test_user_prompt_instructs_jargon_paraphrase(self):
        prompt = DEFAULT_USER_SUMMARIZE_PROMPT.lower()
        paraphrase_signals = ["jargon", "technical term", "everyday word", "plain", "paraphrase"]
        assert any(s in prompt for s in paraphrase_signals), (
            f"user prompt must instruct jargon paraphrasing, got: {prompt!r}"
        )
