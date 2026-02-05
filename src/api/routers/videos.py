"""API endpoints for video listing and retrieval."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from src.api.dependencies import get_db
from src.database.models import Video, AthleteAppearance, Athlete
from src.database.schemas import VideoListItem, VideoResponse, AppearanceInVideo

router = APIRouter(prefix="/videos", tags=["videos"])


@router.get("", response_model=list[VideoListItem])
def list_videos(
    db: Session = Depends(get_db),
):
    """List all processed videos with athlete counts."""
    results = (
        db.query(
            Video.id,
            Video.youtube_id,
            Video.title,
            Video.event_name,
            Video.processed_at,
            func.count(func.distinct(AthleteAppearance.athlete_id)).label("athlete_count"),
        )
        .outerjoin(AthleteAppearance)
        .group_by(Video.id)
        .order_by(Video.processed_at.desc())
        .all()
    )

    return [
        VideoListItem(
            id=r.id,
            youtube_id=r.youtube_id,
            title=r.title,
            event_name=r.event_name,
            processed_at=r.processed_at,
            athlete_count=r.athlete_count,
        )
        for r in results
    ]


@router.get("/{video_id}", response_model=VideoResponse)
def get_video(
    video_id: int,
    db: Session = Depends(get_db),
):
    """Get a single video with all athlete appearances."""
    video = db.get(Video, video_id)

    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    # Build appearances with athlete info
    appearances = []
    for app in video.appearances:
        appearances.append(
            AppearanceInVideo(
                id=app.id,
                athlete_id=app.athlete_id,
                athlete_name=app.athlete.display_name,
                timestamp_seconds=app.timestamp_seconds,
                confidence_score=app.confidence_score,
                youtube_timestamp_url=app.youtube_timestamp_url,
            )
        )

    # Sort appearances by timestamp
    appearances.sort(key=lambda x: x.timestamp_seconds)

    return VideoResponse(
        id=video.id,
        youtube_id=video.youtube_id,
        title=video.title,
        event_name=video.event_name,
        event_date=video.event_date,
        processed_at=video.processed_at,
        appearances=appearances,
    )
