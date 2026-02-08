"""Tests for the processing pipeline."""
import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime

from src.processing.pipeline import ProcessingPipeline, ProcessingResult, PipelineError
from src.processing.transcript_fetcher import FetchedTranscript, TranscriptSegment
from src.processing.llm_extractor import ExtractionResult, AthleteAppearance
from src.processing.youtube_metadata import YouTubeMetadata
from src.database.models import Athlete, Video, AthleteAppearance as DBAthleteAppearance


class TestProcessingResult:
    """Tests for ProcessingResult dataclass."""

    def test_result_creation(self):
        result = ProcessingResult(
            video_id=1,
            youtube_id="abc12345678",
            title="Test Video",
            athletes_found=3,
            appearances_created=5,
        )
        assert result.video_id == 1
        assert result.youtube_id == "abc12345678"
        assert result.already_processed is False

    def test_result_already_processed(self):
        result = ProcessingResult(
            video_id=1,
            youtube_id="abc12345678",
            title="Test",
            athletes_found=2,
            appearances_created=3,
            already_processed=True,
        )
        assert result.already_processed is True


class TestProcessingPipeline:
    """Tests for ProcessingPipeline class."""

    @pytest.fixture
    def mock_fetcher(self):
        fetcher = Mock()
        fetcher.extract_video_id.return_value = "dQw4w9WgXcQ"
        fetcher.fetch.return_value = FetchedTranscript(
            video_id="dQw4w9WgXcQ",
            segments=[
                TranscriptSegment(text="Next up is John Smith", start=15.0, duration=3.0),
                TranscriptSegment(text="John looking strong", start=30.0, duration=2.0),
                TranscriptSegment(text="Now Sarah Johnson", start=120.0, duration=3.0),
            ],
            language="en",
            is_auto_generated=False,
        )
        return fetcher

    @pytest.fixture
    def mock_extractor(self):
        extractor = Mock()
        extractor.extract_appearances.return_value = ExtractionResult(
            video_id="dQw4w9WgXcQ",
            appearances=[
                AthleteAppearance(name="John Smith", timestamp_seconds=15, confidence=0.95),
                AthleteAppearance(name="Sarah Johnson", timestamp_seconds=120, confidence=0.90),
            ],
        )
        return extractor

    @pytest.fixture
    def mock_metadata_fetcher(self):
        fetcher = Mock()
        fetcher.fetch.return_value = YouTubeMetadata(
            video_id="dQw4w9WgXcQ",
            title="Auto Title - 01/01/25 - Tier 1",
            channel_name="Test Channel",
            upload_date=datetime(2025, 1, 1),
            thumbnail_url="https://i.ytimg.com/vi/dQw4w9WgXcQ/mqdefault.jpg",
        )
        return fetcher

    def test_process_video_success(self, test_session, mock_fetcher, mock_extractor, mock_metadata_fetcher):
        pipeline = ProcessingPipeline(
            db=test_session,
            transcript_fetcher=mock_fetcher,
            llm_extractor=mock_extractor,
            metadata_fetcher=mock_metadata_fetcher,
        )

        result = pipeline.process_video(
            url_or_id="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            title="Test Competition",
            event_name="WNL Test Event",
        )

        assert result.video_id is not None
        assert result.youtube_id == "dQw4w9WgXcQ"
        assert result.athletes_found == 2
        assert result.appearances_created == 2
        assert result.already_processed is False

        # Verify database records
        video = test_session.query(Video).filter_by(youtube_id="dQw4w9WgXcQ").first()
        assert video is not None
        assert video.title == "Test Competition"
        assert len(video.appearances) == 2

    def test_process_video_idempotent(self, test_session, mock_fetcher, mock_extractor, mock_metadata_fetcher):
        """Second processing should return already_processed=True."""
        pipeline = ProcessingPipeline(
            db=test_session,
            transcript_fetcher=mock_fetcher,
            llm_extractor=mock_extractor,
            metadata_fetcher=mock_metadata_fetcher,
        )

        # First processing
        result1 = pipeline.process_video("dQw4w9WgXcQ", title="Test")
        assert result1.already_processed is False

        # Second processing - should skip
        result2 = pipeline.process_video("dQw4w9WgXcQ")
        assert result2.already_processed is True
        assert result2.video_id == result1.video_id

        # Verify only one video was created
        videos = test_session.query(Video).all()
        assert len(videos) == 1

    def test_process_video_force_reprocess(self, test_session, mock_fetcher, mock_extractor, mock_metadata_fetcher):
        """Force reprocess should update the video."""
        pipeline = ProcessingPipeline(
            db=test_session,
            transcript_fetcher=mock_fetcher,
            llm_extractor=mock_extractor,
            metadata_fetcher=mock_metadata_fetcher,
        )

        # First processing
        result1 = pipeline.process_video("dQw4w9WgXcQ", title="Original Title")
        assert result1.already_processed is False

        # Force reprocess
        result2 = pipeline.process_video(
            "dQw4w9WgXcQ",
            title="Updated Title",
            force_reprocess=True,
        )
        assert result2.already_processed is False
        assert result2.video_id == result1.video_id

        # Verify video was updated
        video = test_session.get(Video, result1.video_id)
        assert video.title == "Updated Title"

    def test_process_video_invalid_url(self, test_session, mock_fetcher, mock_extractor, mock_metadata_fetcher):
        mock_fetcher.extract_video_id.side_effect = ValueError("Invalid URL")

        pipeline = ProcessingPipeline(
            db=test_session,
            transcript_fetcher=mock_fetcher,
            llm_extractor=mock_extractor,
            metadata_fetcher=mock_metadata_fetcher,
        )

        with pytest.raises(PipelineError, match="Invalid video URL"):
            pipeline.process_video("not-a-valid-url")

    def test_process_video_transcript_error(self, test_session, mock_fetcher, mock_extractor, mock_metadata_fetcher):
        from src.processing.transcript_fetcher import TranscriptFetchError

        mock_fetcher.fetch.side_effect = TranscriptFetchError("No transcript")

        pipeline = ProcessingPipeline(
            db=test_session,
            transcript_fetcher=mock_fetcher,
            llm_extractor=mock_extractor,
            metadata_fetcher=mock_metadata_fetcher,
        )

        with pytest.raises(PipelineError, match="Failed to fetch transcript"):
            pipeline.process_video("dQw4w9WgXcQ")

    def test_process_video_llm_error(self, test_session, mock_fetcher, mock_extractor, mock_metadata_fetcher):
        from src.processing.llm_extractor import LLMExtractorError

        mock_extractor.extract_appearances.side_effect = LLMExtractorError("API error")

        pipeline = ProcessingPipeline(
            db=test_session,
            transcript_fetcher=mock_fetcher,
            llm_extractor=mock_extractor,
            metadata_fetcher=mock_metadata_fetcher,
        )

        with pytest.raises(PipelineError, match="Failed to extract athletes"):
            pipeline.process_video("dQw4w9WgXcQ")

    def test_find_or_create_athlete_creates_new(self, test_session, mock_fetcher, mock_extractor, mock_metadata_fetcher):
        pipeline = ProcessingPipeline(
            db=test_session,
            transcript_fetcher=mock_fetcher,
            llm_extractor=mock_extractor,
            metadata_fetcher=mock_metadata_fetcher,
        )

        athlete = pipeline._find_or_create_athlete("New Athlete Name")

        assert athlete.id is not None
        assert athlete.display_name == "New Athlete Name"

        # Verify in database
        db_athlete = test_session.query(Athlete).filter_by(display_name="New Athlete Name").first()
        assert db_athlete is not None

    def test_find_or_create_athlete_finds_existing(self, test_session, mock_fetcher, mock_extractor, mock_metadata_fetcher):
        # Create existing athlete
        existing = Athlete(display_name="Existing Athlete")
        test_session.add(existing)
        test_session.commit()

        pipeline = ProcessingPipeline(
            db=test_session,
            transcript_fetcher=mock_fetcher,
            llm_extractor=mock_extractor,
            metadata_fetcher=mock_metadata_fetcher,
        )

        # Should find existing (case insensitive)
        found = pipeline._find_or_create_athlete("existing athlete")

        assert found.id == existing.id

    def test_find_or_create_athlete_finds_by_alias(self, test_session, mock_fetcher, mock_extractor, mock_metadata_fetcher):
        # Create athlete with aliases
        existing = Athlete(
            display_name="Robert Johnson",
            aliases=["Rob Johnson", "Bobby J"],
        )
        test_session.add(existing)
        test_session.commit()

        pipeline = ProcessingPipeline(
            db=test_session,
            transcript_fetcher=mock_fetcher,
            llm_extractor=mock_extractor,
            metadata_fetcher=mock_metadata_fetcher,
        )

        # Should find by alias
        found = pipeline._find_or_create_athlete("rob johnson")

        assert found.id == existing.id
        assert found.display_name == "Robert Johnson"

    def test_process_creates_correct_appearances(self, test_session, mock_fetcher, mock_extractor, mock_metadata_fetcher):
        pipeline = ProcessingPipeline(
            db=test_session,
            transcript_fetcher=mock_fetcher,
            llm_extractor=mock_extractor,
            metadata_fetcher=mock_metadata_fetcher,
        )

        pipeline.process_video("dQw4w9WgXcQ", title="Test")

        # Check appearances
        appearances = test_session.query(DBAthleteAppearance).all()
        assert len(appearances) == 2

        # Check John Smith appearance
        john_app = next(a for a in appearances if a.raw_name_in_transcript == "John Smith")
        assert john_app.timestamp_seconds == 15
        assert john_app.confidence_score == 0.95

        # Check Sarah Johnson appearance
        sarah_app = next(a for a in appearances if a.raw_name_in_transcript == "Sarah Johnson")
        assert sarah_app.timestamp_seconds == 120
        assert sarah_app.confidence_score == 0.90

    def test_auto_fetched_title_when_none_provided(self, test_session, mock_fetcher, mock_extractor, mock_metadata_fetcher):
        """When title=None, pipeline uses auto-fetched title from YouTube."""
        pipeline = ProcessingPipeline(
            db=test_session,
            transcript_fetcher=mock_fetcher,
            llm_extractor=mock_extractor,
            metadata_fetcher=mock_metadata_fetcher,
        )

        result = pipeline.process_video("dQw4w9WgXcQ")

        video = test_session.query(Video).filter_by(youtube_id="dQw4w9WgXcQ").first()
        assert video.title == "Auto Title - 01/01/25 - Tier 1"
        assert video.channel_name == "Test Channel"
        assert video.event_name == "Auto Title"
        assert video.event_date == datetime(2025, 1, 1)

    def test_explicit_title_overrides_fetched(self, test_session, mock_fetcher, mock_extractor, mock_metadata_fetcher):
        """When title is explicitly provided, it overrides the fetched title."""
        pipeline = ProcessingPipeline(
            db=test_session,
            transcript_fetcher=mock_fetcher,
            llm_extractor=mock_extractor,
            metadata_fetcher=mock_metadata_fetcher,
        )

        result = pipeline.process_video("dQw4w9WgXcQ", title="My Custom Title")

        video = test_session.query(Video).filter_by(youtube_id="dQw4w9WgXcQ").first()
        assert video.title == "My Custom Title"
        # channel_name should still come from metadata
        assert video.channel_name == "Test Channel"
