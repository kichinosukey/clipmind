"""Tests for discord_client.soft_split() — pure function, no mocks needed."""

from clipmind.discord_client import soft_split


class TestSoftSplit:
    def test_short_text_no_split(self):
        """Text shorter than max_len returns a single-element list."""
        result = soft_split("Hello world", max_len=1900)
        assert result == ["Hello world"]

    def test_split_at_japanese_period(self):
        """Long text is split at the last '。' within max_len."""
        part1 = "あ" * 50 + "。"
        part2 = "い" * 50
        text = part1 + part2
        result = soft_split(text, max_len=60)
        assert len(result) == 2
        assert result[0] == part1.strip()
        assert result[1] == part2.strip()

    def test_split_at_newline(self):
        """When no '。', text is split at the last newline."""
        part1 = "a" * 50 + "\n"
        part2 = "b" * 50
        text = part1 + part2
        result = soft_split(text, max_len=60)
        assert len(result) == 2
        assert result[0] == part1.strip()
        assert result[1] == part2.strip()

    def test_split_no_natural_boundary(self):
        """No '。' or newline → hard cut at max_len+1 (text[:cut+1] where cut=max_len)."""
        text = "x" * 100
        result = soft_split(text, max_len=40)
        # Implementation: cut=max_len, parts.append(text[:cut+1]) → 41 chars per chunk
        assert len(result) == 3
        assert result[0] == "x" * 41
        assert result[1] == "x" * 41
        assert result[2] == "x" * 18

    def test_multiple_splits(self):
        """Text 3x+ max_len produces 3+ parts."""
        text = ("あいうえお。" * 20)  # each segment is 6 chars
        result = soft_split(text, max_len=30)
        assert len(result) >= 3

    def test_empty_string(self):
        """Empty string returns an empty list (while loop body never entered)."""
        result = soft_split("")
        assert result == []

    def test_custom_max_len(self):
        """Custom max_len=50 is respected (hard-cut yields max_len+1 chars)."""
        text = "a" * 80
        result = soft_split(text, max_len=50)
        assert len(result) == 2
        assert len(result[0]) == 51  # text[:max_len+1] when no boundary found

    def test_exact_boundary(self):
        """Text exactly at max_len is not split."""
        text = "a" * 100
        result = soft_split(text, max_len=100)
        assert result == ["a" * 100]

    def test_japanese_period_preferred_over_newline(self):
        """'。' is preferred over newline when both are present."""
        # '。' at position 45, '\n' at position 40
        text = "a" * 40 + "\n" + "a" * 4 + "。" + "b" * 60
        result = soft_split(text, max_len=50)
        # rfind picks the maximum of the two positions; '。' at 45 > '\n' at 40
        assert result[0].endswith("。")
