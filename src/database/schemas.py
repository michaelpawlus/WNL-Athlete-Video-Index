"""Pydantic schemas for API request/response models."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


# --- Athlete Schemas ---


class AthleteBase(BaseModel):
    """Base schema for athlete data."""

    display_name: str
    aliases: list[str] = []


class AthleteCreate(AthleteBase):
    """Schema for creating an athlete."""

    pass


class AppearanceInAthlete(BaseModel):
    """Appearance info nested within athlete response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    video_id: int
    youtube_id: str
    video_title: Optional[str]
    timestamp_seconds: int
    confidence_score: float
    youtube_timestamp_url: str


class AthleteResponse(AthleteBase):
    """Schema for athlete API response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    appearances: list[AppearanceInAthlete] = []


class AthleteSearchResult(BaseModel):
    """Schema for athlete search results."""

    id: Optional[int] = None
    display_name: str
    appearance_count: int = 0
    similarity_score: float = 0.0
    matched_on: Optional[str] = None
    source: str = "db"


# --- Video Schemas ---


class VideoBase(BaseModel):
    """Base schema for video data."""

    youtube_id: str
    title: Optional[str] = None
    event_name: Optional[str] = None
    event_date: Optional[datetime] = None
    channel_name: Optional[str] = None


class VideoCreate(VideoBase):
    """Schema for creating a video."""

    transcript_raw: Optional[str] = None


class AppearanceInVideo(BaseModel):
    """Appearance info nested within video response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    athlete_id: int
    athlete_name: str
    timestamp_seconds: int
    confidence_score: float
    youtube_timestamp_url: str


class VideoResponse(VideoBase):
    """Schema for video API response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    processed_at: datetime
    appearances: list[AppearanceInVideo] = []


class VideoListItem(BaseModel):
    """Schema for video list response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    youtube_id: str
    title: Optional[str]
    event_name: Optional[str]
    event_date: Optional[datetime] = None
    channel_name: Optional[str] = None
    processed_at: datetime
    athlete_count: int


# --- Processing Schemas ---


class ProcessVideoRequest(BaseModel):
    """Schema for video processing request."""

    url: str
    title: Optional[str] = None
    event_name: Optional[str] = None
    event_date: Optional[datetime] = None


class ProcessVideoResponse(BaseModel):
    """Schema for video processing response."""

    video_id: int
    youtube_id: str
    athletes_found: int
    appearances_created: int
    message: str
