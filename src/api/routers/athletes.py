"""API endpoints for athlete search and retrieval."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from src.api.dependencies import get_db
from src.database.models import Athlete, AthleteAppearance, Video
from src.database.schemas import AthleteSearchResult, AthleteResponse, AppearanceInAthlete

router = APIRouter(prefix="/athletes", tags=["athletes"])


@router.get("/search", response_model=list[AthleteSearchResult])
def search_athletes(
    q: str = Query(..., min_length=1, description="Search query for athlete name"),
    limit: int = Query(20, ge=1, le=100, description="Maximum results to return"),
    db: Session = Depends(get_db),
):
    """Search for athletes by name (partial match).

    Returns athletes with matching names and their appearance counts.
    """
    search_pattern = f"%{q}%"

    # Query athletes with appearance count
    results = (
        db.query(
            Athlete.id,
            Athlete.display_name,
            func.count(AthleteAppearance.id).label("appearance_count"),
        )
        .outerjoin(AthleteAppearance)
        .filter(Athlete.display_name.ilike(search_pattern))
        .group_by(Athlete.id)
        .order_by(func.count(AthleteAppearance.id).desc())
        .limit(limit)
        .all()
    )

    return [
        AthleteSearchResult(
            id=r.id,
            display_name=r.display_name,
            appearance_count=r.appearance_count,
        )
        for r in results
    ]


@router.get("/{athlete_id}", response_model=AthleteResponse)
def get_athlete(
    athlete_id: int,
    db: Session = Depends(get_db),
):
    """Get a single athlete with all their video appearances."""
    athlete = db.get(Athlete, athlete_id)

    if not athlete:
        raise HTTPException(status_code=404, detail="Athlete not found")

    # Build appearances with video info
    appearances = []
    for app in athlete.appearances:
        appearances.append(
            AppearanceInAthlete(
                id=app.id,
                video_id=app.video_id,
                youtube_id=app.video.youtube_id,
                video_title=app.video.title,
                timestamp_seconds=app.timestamp_seconds,
                confidence_score=app.confidence_score,
                youtube_timestamp_url=app.youtube_timestamp_url,
            )
        )

    return AthleteResponse(
        id=athlete.id,
        display_name=athlete.display_name,
        aliases=athlete.aliases or [],
        created_at=athlete.created_at,
        appearances=appearances,
    )
