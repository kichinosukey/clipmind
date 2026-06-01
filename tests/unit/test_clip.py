"""Tests for clipmind.clip — Clip dataclass."""

from clipmind.clip import Clip


class TestClip:
    def test_create_with_all_fields(self):
        clip = Clip(
            source_type="youtube",
            url="https://youtu.be/abc",
            title="Test Video",
            author="TestChannel",
            author_url="https://youtube.com/@TestChannel",
            audio_path="/tmp/test.wav",
            transcript="Hello world",
            summary_en="English summary",
            summary_ja="日本語要約",
            metadata={"key": "value"},
        )
        assert clip.source_type == "youtube"
        assert clip.title == "Test Video"
        assert clip.metadata == {"key": "value"}

    def test_create_with_defaults(self):
        clip = Clip(
            source_type="youtube",
            url="https://youtu.be/abc",
            title="Test",
            author="Ch",
            author_url="https://youtube.com/@Ch",
        )
        assert clip.audio_path is None
        assert clip.transcript is None
        assert clip.summary_en is None
        assert clip.summary_ja is None
        assert clip.metadata == {}

    def test_metadata_default_is_independent(self):
        """Each Clip gets its own metadata dict."""
        a = Clip(source_type="youtube", url="u", title="t", author="a", author_url="au")
        b = Clip(source_type="youtube", url="u", title="t", author="a", author_url="au")
        a.metadata["x"] = 1
        assert "x" not in b.metadata
