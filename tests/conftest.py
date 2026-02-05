"""Shared pytest fixtures for tests."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database.connection import Base
from src.database.models import Athlete, Video, AthleteAppearance


@pytest.fixture(scope="function")
def test_engine():
    """Create an in-memory SQLite engine for testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def test_session(test_engine):
    """Create a test database session."""
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = TestSessionLocal()
    yield session
    session.close()


@pytest.fixture
def sample_athlete(test_session):
    """Create a sample athlete for testing."""
    athlete = Athlete(display_name="John Smith", aliases=["Johnny Smith", "J. Smith"])
    test_session.add(athlete)
    test_session.commit()
    test_session.refresh(athlete)
    return athlete


@pytest.fixture
def sample_video(test_session):
    """Create a sample video for testing."""
    video = Video(
        youtube_id="dQw4w9WgXcQ",
        title="WNL Season 5 - Episode 1",
        event_name="World Ninja League Season 5",
        transcript_raw="[00:15] Next up is John Smith from Denver",
    )
    test_session.add(video)
    test_session.commit()
    test_session.refresh(video)
    return video


@pytest.fixture
def sample_appearance(test_session, sample_athlete, sample_video):
    """Create a sample appearance linking athlete and video."""
    appearance = AthleteAppearance(
        athlete_id=sample_athlete.id,
        video_id=sample_video.id,
        timestamp_seconds=15,
        confidence_score=0.95,
        raw_name_in_transcript="John Smith",
    )
    test_session.add(appearance)
    test_session.commit()
    test_session.refresh(appearance)
    return appearance
