"""Tests for transcript fetcher module."""
import pytest
from unittest.mock import Mock, patch

from src.processing.transcript_fetcher import (
    TranscriptFetcher,
    TranscriptSegment,
    FetchedTranscript,
    TranscriptFetchError,
)


class TestTranscriptSegment:
    """Tests for TranscriptSegment dataclass."""

    def test_segment_creation(self):
        segment = TranscriptSegment(text="Hello world", start=10.5, duration=3.2)
        assert segment.text == "Hello world"
        assert segment.start == 10.5
        assert segment.duration == 3.2

    def test_segment_end_property(self):
        segment = TranscriptSegment(text="Test", start=10.0, duration=5.0)
        assert segment.end == 15.0


class TestFetchedTranscript:
    """Tests for FetchedTranscript dataclass."""

    def test_full_text_property(self):
        segments = [
            TranscriptSegment(text="Hello", start=0.0, duration=1.0),
            TranscriptSegment(text="world", start=1.0, duration=1.0),
        ]
        transcript = FetchedTranscript(
            video_id="test123",
            segments=segments,
            language="en",
            is_auto_generated=False,
        )
        assert transcript.full_text == "Hello world"

    def test_text_with_timestamps(self):
        segments = [
            TranscriptSegment(text="First segment", start=0.0, duration=5.0),
            TranscriptSegment(text="Second segment", start=65.0, duration=5.0),
            TranscriptSegment(text="Third segment", start=125.5, duration=5.0),
        ]
        transcript = FetchedTranscript(
            video_id="test123",
            segments=segments,
            language="en",
            is_auto_generated=True,
        )
        expected = "[00:00] First segment\n[01:05] Second segment\n[02:05] Third segment"
        assert transcript.text_with_timestamps == expected

    def test_duration_seconds(self):
        segments = [
            TranscriptSegment(text="First", start=0.0, duration=10.0),
            TranscriptSegment(text="Last", start=50.0, duration=15.0),
        ]
        transcript = FetchedTranscript(
            video_id="test123",
            segments=segments,
            language="en",
            is_auto_generated=False,
        )
        assert transcript.duration_seconds == 65.0

    def test_duration_empty_transcript(self):
        transcript = FetchedTranscript(
            video_id="test123",
            segments=[],
            language="en",
            is_auto_generated=False,
        )
        assert transcript.duration_seconds == 0.0


class TestTranscriptFetcher:
    """Tests for TranscriptFetcher class."""

    @pytest.fixture
    def fetcher(self):
        return TranscriptFetcher()

    def test_extract_video_id_standard_url(self, fetcher):
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        assert fetcher.extract_video_id(url) == "dQw4w9WgXcQ"

    def test_extract_video_id_with_extra_params(self, fetcher):
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=120"
        assert fetcher.extract_video_id(url) == "dQw4w9WgXcQ"

    def test_extract_video_id_short_url(self, fetcher):
        url = "https://youtu.be/dQw4w9WgXcQ"
        assert fetcher.extract_video_id(url) == "dQw4w9WgXcQ"

    def test_extract_video_id_embed_url(self, fetcher):
        url = "https://www.youtube.com/embed/dQw4w9WgXcQ"
        assert fetcher.extract_video_id(url) == "dQw4w9WgXcQ"

    def test_extract_video_id_shorts_url(self, fetcher):
        url = "https://www.youtube.com/shorts/dQw4w9WgXcQ"
        assert fetcher.extract_video_id(url) == "dQw4w9WgXcQ"

    def test_extract_video_id_just_id(self, fetcher):
        video_id = "dQw4w9WgXcQ"
        assert fetcher.extract_video_id(video_id) == "dQw4w9WgXcQ"

    def test_extract_video_id_with_whitespace(self, fetcher):
        url = "  https://youtu.be/dQw4w9WgXcQ  "
        assert fetcher.extract_video_id(url) == "dQw4w9WgXcQ"

    def test_extract_video_id_invalid_url(self, fetcher):
        with pytest.raises(ValueError, match="Could not extract video ID"):
            fetcher.extract_video_id("https://example.com/not-youtube")

    def test_extract_video_id_invalid_short_id(self, fetcher):
        with pytest.raises(ValueError, match="Could not extract video ID"):
            fetcher.extract_video_id("abc123")  # Too short

    @patch("src.processing.transcript_fetcher.YouTubeTranscriptApi")
    def test_fetch_success(self, mock_api, fetcher):
        # Mock the transcript list and transcript
        mock_transcript = Mock()
        mock_transcript.language_code = "en"
        mock_transcript.is_generated = False
        mock_transcript.fetch.return_value = [
            {"text": "Hello", "start": 0.0, "duration": 2.0},
            {"text": "World", "start": 2.0, "duration": 2.0},
        ]

        mock_transcript_list = Mock()
        mock_transcript_list.find_manually_created_transcript.return_value = (
            mock_transcript
        )
        mock_api.list_transcripts.return_value = mock_transcript_list

        result = fetcher.fetch("dQw4w9WgXcQ")

        assert result.video_id == "dQw4w9WgXcQ"
        assert len(result.segments) == 2
        assert result.language == "en"
        assert result.is_auto_generated is False
        assert result.segments[0].text == "Hello"
        assert result.segments[1].start == 2.0

    @patch("src.processing.transcript_fetcher.YouTubeTranscriptApi")
    def test_fetch_falls_back_to_auto_generated(self, mock_api, fetcher):
        from youtube_transcript_api._errors import NoTranscriptFound

        mock_auto_transcript = Mock()
        mock_auto_transcript.language_code = "en"
        mock_auto_transcript.is_generated = True
        mock_auto_transcript.fetch.return_value = [
            {"text": "Auto text", "start": 0.0, "duration": 1.0}
        ]

        mock_transcript_list = Mock()
        mock_transcript_list.find_manually_created_transcript.side_effect = (
            NoTranscriptFound("test", ["en"], {})
        )
        mock_transcript_list.find_generated_transcript.return_value = mock_auto_transcript
        mock_api.list_transcripts.return_value = mock_transcript_list

        result = fetcher.fetch("dQw4w9WgXcQ")

        assert result.is_auto_generated is True
        assert result.segments[0].text == "Auto text"
