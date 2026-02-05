"""Tests for database models and operations."""
import pytest
from datetime import datetime

from src.database.models import Athlete, Video, AthleteAppearance


class TestAthleteModel:
    """Tests for the Athlete model."""

    def test_create_athlete(self, test_session):
        athlete = Athlete(display_name="Jane Doe")
        test_session.add(athlete)
        test_session.commit()

        assert athlete.id is not None
        assert athlete.display_name == "Jane Doe"
        assert athlete.aliases == []
        assert athlete.created_at is not None

    def test_athlete_with_aliases(self, test_session):
        athlete = Athlete(
            display_name="Robert Johnson",
            aliases=["Rob Johnson", "Bobby Johnson"],
        )
        test_session.add(athlete)
        test_session.commit()

        retrieved = test_session.query(Athlete).filter_by(display_name="Robert Johnson").first()
        assert retrieved.aliases == ["Rob Johnson", "Bobby Johnson"]

    def test_athlete_repr(self, sample_athlete):
        repr_str = repr(sample_athlete)
        assert "Athlete" in repr_str
        assert "John Smith" in repr_str


class TestVideoModel:
    """Tests for the Video model."""

    def test_create_video(self, test_session):
        video = Video(
            youtube_id="abc12345678",
            title="Test Video",
        )
        test_session.add(video)
        test_session.commit()

        assert video.id is not None
        assert video.youtube_id == "abc12345678"
        assert video.processed_at is not None

    def test_video_unique_youtube_id(self, test_session):
        video1 = Video(youtube_id="unique12345")
        test_session.add(video1)
        test_session.commit()

        video2 = Video(youtube_id="unique12345")
        test_session.add(video2)

        with pytest.raises(Exception):  # IntegrityError
            test_session.commit()

    def test_video_with_event_info(self, test_session):
        event_date = datetime(2024, 6, 15)
        video = Video(
            youtube_id="event123456",
            title="Competition Finals",
            event_name="WNL Finals 2024",
            event_date=event_date,
        )
        test_session.add(video)
        test_session.commit()

        assert video.event_name == "WNL Finals 2024"
        assert video.event_date == event_date


class TestAthleteAppearanceModel:
    """Tests for the AthleteAppearance model."""

    def test_create_appearance(self, test_session, sample_athlete, sample_video):
        appearance = AthleteAppearance(
            athlete_id=sample_athlete.id,
            video_id=sample_video.id,
            timestamp_seconds=120,
            confidence_score=0.85,
            raw_name_in_transcript="John Smith",
        )
        test_session.add(appearance)
        test_session.commit()

        assert appearance.id is not None
        assert appearance.timestamp_seconds == 120
        assert appearance.confidence_score == 0.85

    def test_appearance_relationships(self, sample_appearance, sample_athlete, sample_video):
        assert sample_appearance.athlete.id == sample_athlete.id
        assert sample_appearance.video.id == sample_video.id

    def test_youtube_timestamp_url(self, sample_appearance):
        url = sample_appearance.youtube_timestamp_url
        assert "youtube.com/watch" in url
        assert sample_appearance.video.youtube_id in url
        assert "t=15s" in url

    def test_athlete_has_appearances(self, test_session, sample_appearance):
        athlete = test_session.get(Athlete, sample_appearance.athlete_id)
        assert len(athlete.appearances) == 1
        assert athlete.appearances[0].timestamp_seconds == 15

    def test_video_has_appearances(self, test_session, sample_appearance):
        video = test_session.get(Video, sample_appearance.video_id)
        assert len(video.appearances) == 1
        assert video.appearances[0].athlete.display_name == "John Smith"


class TestCascadeDelete:
    """Tests for cascade delete behavior."""

    def test_delete_athlete_deletes_appearances(self, test_session, sample_appearance):
        athlete_id = sample_appearance.athlete_id
        appearance_id = sample_appearance.id

        # Delete the athlete
        athlete = test_session.get(Athlete, athlete_id)
        test_session.delete(athlete)
        test_session.commit()

        # Appearance should be deleted too
        appearance = test_session.get(AthleteAppearance, appearance_id)
        assert appearance is None

    def test_delete_video_deletes_appearances(self, test_session, sample_appearance):
        video_id = sample_appearance.video_id
        appearance_id = sample_appearance.id

        # Delete the video
        video = test_session.get(Video, video_id)
        test_session.delete(video)
        test_session.commit()

        # Appearance should be deleted too
        appearance = test_session.get(AthleteAppearance, appearance_id)
        assert appearance is None
