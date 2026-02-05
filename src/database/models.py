"""SQLAlchemy ORM models for the athlete video index."""
from datetime import datetime, timezone
from typing import Optional


def utc_now() -> datetime:
    """Return current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    DateTime,
    Text,
    ForeignKey,
    JSON,
)
from sqlalchemy.orm import relationship

from .connection import Base


class Athlete(Base):
    """Athlete model representing a ninja warrior competitor."""

    __tablename__ = "athletes"

    id = Column(Integer, primary_key=True, index=True)
    display_name = Column(String(255), nullable=False, index=True)
    aliases = Column(JSON, default=list)  # List of alternative names
    created_at = Column(DateTime, default=utc_now)

    # Relationships
    appearances = relationship(
        "AthleteAppearance", back_populates="athlete", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Athlete(id={self.id}, name='{self.display_name}')>"


class Video(Base):
    """Video model representing a processed YouTube video."""

    __tablename__ = "videos"

    id = Column(Integer, primary_key=True, index=True)
    youtube_id = Column(String(11), unique=True, nullable=False, index=True)
    title = Column(String(500), nullable=True)
    event_name = Column(String(255), nullable=True)
    event_date = Column(DateTime, nullable=True)
    transcript_raw = Column(Text, nullable=True)
    processed_at = Column(DateTime, default=utc_now)

    # Relationships
    appearances = relationship(
        "AthleteAppearance", back_populates="video", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Video(id={self.id}, youtube_id='{self.youtube_id}')>"


class AthleteAppearance(Base):
    """Link between an athlete and a video with timestamp information."""

    __tablename__ = "athlete_appearances"

    id = Column(Integer, primary_key=True, index=True)
    athlete_id = Column(Integer, ForeignKey("athletes.id"), nullable=False, index=True)
    video_id = Column(Integer, ForeignKey("videos.id"), nullable=False, index=True)
    timestamp_seconds = Column(Integer, nullable=False)
    confidence_score = Column(Float, default=1.0)
    raw_name_in_transcript = Column(String(255), nullable=True)  # Original name from transcript
    verified = Column(Boolean, default=False)  # Manual verification flag

    # Relationships
    athlete = relationship("Athlete", back_populates="appearances")
    video = relationship("Video", back_populates="appearances")

    @property
    def youtube_timestamp_url(self) -> str:
        """Generate YouTube URL with timestamp parameter."""
        return f"https://www.youtube.com/watch?v={self.video.youtube_id}&t={self.timestamp_seconds}s"

    def __repr__(self) -> str:
        return f"<AthleteAppearance(athlete_id={self.athlete_id}, video_id={self.video_id}, t={self.timestamp_seconds}s)>"
