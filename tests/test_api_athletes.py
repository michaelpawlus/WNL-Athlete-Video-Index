"""Tests for athlete API endpoints."""
import os
import pytest
from unittest.mock import patch, Mock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.api.main import app
from src.api.dependencies import get_db
from src.database.connection import Base
from src.database.models import Athlete, Video, AthleteAppearance


# Create a single connection pool for all tests to share the same in-memory database
test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="function")
def db_session():
    """Create tables and provide a session for each test."""
    Base.metadata.create_all(bind=test_engine)
    session = TestSessionLocal()

    # Override the dependency
    def override_get_db():
        try:
            yield session
        finally:
            pass  # Don't close - we manage it in the fixture

    app.dependency_overrides[get_db] = override_get_db

    yield session

    session.close()
    Base.metadata.drop_all(bind=test_engine)
    app.dependency_overrides.clear()


@pytest.fixture
def client(db_session):
    """Create test client (depends on db_session for proper ordering)."""
    return TestClient(app)


@pytest.fixture
def sample_data(db_session):
    """Create sample athletes, videos, and appearances for testing."""
    # Create athletes
    john = Athlete(display_name="John Smith", aliases=["Johnny S"])
    sarah = Athlete(display_name="Sarah Johnson")
    db_session.add_all([john, sarah])
    db_session.commit()

    # Create video
    video = Video(
        youtube_id="dQw4w9WgXcQ",
        title="WNL Season 5 Episode 1",
        event_name="WNL Season 5",
    )
    db_session.add(video)
    db_session.commit()

    # Create appearances
    app1 = AthleteAppearance(
        athlete_id=john.id,
        video_id=video.id,
        timestamp_seconds=15,
        confidence_score=0.95,
        raw_name_in_transcript="John Smith",
    )
    app2 = AthleteAppearance(
        athlete_id=sarah.id,
        video_id=video.id,
        timestamp_seconds=120,
        confidence_score=0.88,
        raw_name_in_transcript="Sarah Johnson",
    )
    db_session.add_all([app1, app2])
    db_session.commit()

    return {"john": john, "sarah": sarah, "video": video}


class TestHealthEndpoint:
    """Tests for health check endpoint."""

    def test_health_check(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}

    def test_root_endpoint(self, client):
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "WNL Athlete Video Index" in data["name"]


class TestAthleteSearchEndpoint:
    """Tests for athlete search endpoint."""

    def test_search_athletes_by_name(self, client, sample_data):
        response = client.get("/api/athletes/search?q=smith")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["display_name"] == "John Smith"
        assert data[0]["appearance_count"] == 1

    def test_search_athletes_partial_match(self, client, sample_data):
        response = client.get("/api/athletes/search?q=son")
        assert response.status_code == 200
        data = response.json()
        # Should match "Sarah Johnson"
        assert len(data) == 1
        assert data[0]["display_name"] == "Sarah Johnson"

    def test_search_athletes_no_results(self, client, sample_data):
        response = client.get("/api/athletes/search?q=xyz")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0

    def test_search_athletes_requires_query(self, client):
        response = client.get("/api/athletes/search")
        assert response.status_code == 422  # Validation error

    def test_search_athletes_case_insensitive(self, client, sample_data):
        response = client.get("/api/athletes/search?q=SMITH")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["display_name"] == "John Smith"

    def test_search_athletes_with_limit(self, client, sample_data):
        response = client.get("/api/athletes/search?q=s&limit=1")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1


class TestAthleteGetEndpoint:
    """Tests for getting a single athlete."""

    def test_get_athlete_with_appearances(self, client, sample_data):
        athlete_id = sample_data["john"].id
        response = client.get(f"/api/athletes/{athlete_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["display_name"] == "John Smith"
        assert len(data["appearances"]) == 1
        assert data["appearances"][0]["timestamp_seconds"] == 15
        assert "youtube.com/watch" in data["appearances"][0]["youtube_timestamp_url"]
        assert "t=15s" in data["appearances"][0]["youtube_timestamp_url"]

    def test_get_athlete_not_found(self, client):
        response = client.get("/api/athletes/99999")
        assert response.status_code == 404


class TestVideoEndpoints:
    """Tests for video endpoints."""

    def test_list_videos(self, client, sample_data):
        response = client.get("/api/videos")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["youtube_id"] == "dQw4w9WgXcQ"
        assert data[0]["athlete_count"] == 2

    def test_get_video_with_appearances(self, client, sample_data):
        video_id = sample_data["video"].id
        response = client.get(f"/api/videos/{video_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["youtube_id"] == "dQw4w9WgXcQ"
        assert len(data["appearances"]) == 2
        # Appearances should be sorted by timestamp
        assert data["appearances"][0]["timestamp_seconds"] < data["appearances"][1]["timestamp_seconds"]

    def test_get_video_not_found(self, client):
        response = client.get("/api/videos/99999")
        assert response.status_code == 404


class TestProcessingEndpoint:
    """Tests for video processing endpoint."""

    def test_process_video_endpoint_exists(self, client):
        # Just test that the endpoint exists and rejects missing data
        response = client.post("/api/processing/video", json={})
        assert response.status_code == 422  # Missing required field "url"

    @patch("src.api.routers.processing.ProcessingPipeline")
    def test_process_video_success(self, mock_pipeline_class, client):
        # Mock the pipeline
        mock_pipeline = Mock()
        mock_pipeline.process_video.return_value = Mock(
            video_id=1,
            youtube_id="test12345ab",
            athletes_found=3,
            appearances_created=5,
            already_processed=False,
        )
        mock_pipeline_class.return_value = mock_pipeline

        response = client.post(
            "/api/processing/video",
            json={"url": "https://www.youtube.com/watch?v=test12345ab"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["youtube_id"] == "test12345ab"
        assert data["athletes_found"] == 3
        assert data["appearances_created"] == 5
        assert data["message"] == "Video processed successfully"
