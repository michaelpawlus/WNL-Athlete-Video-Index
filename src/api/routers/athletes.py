"""API endpoints for athlete search and retrieval."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from src.api.dependencies import get_db
from src.database.models import Athlete, AthleteAppearance, Video
from src.database.schemas import AthleteSearchResult, AthleteResponse, AppearanceInAthlete
from src.search.fuzzy import build_search_candidates, fuzzy_search
from src.search.known_athletes import load_known_athletes

router = APIRouter(prefix="/athletes", tags=["athletes"])


@router.get("/search", response_model=list[AthleteSearchResult])
def search_athletes(
    q: str = Query(..., min_length=1, description="Search query for athlete name"),
    limit: int = Query(10, ge=1, le=100, description="Maximum results to return"),
    threshold: int = Query(45, ge=0, le=100, description="Minimum fuzzy score"),
    db: Session = Depends(get_db),
):
    """Search for athletes by name using fuzzy matching.

    Returns athletes with matching names, similarity scores, and appearance counts.
    """
    # Load all athletes with appearance counts
    rows = (
        db.query(
            Athlete.id,
            Athlete.display_name,
            Athlete.aliases,
            func.count(AthleteAppearance.id).label("appearance_count"),
        )
        .outerjoin(AthleteAppearance)
        .group_by(Athlete.id)
        .all()
    )

    db_athletes = [
        {
            "id": r.id,
            "display_name": r.display_name,
            "aliases": r.aliases or [],
            "appearance_count": r.appearance_count,
        }
        for r in rows
    ]

    # Build candidates from DB athletes + known athletes registry
    known = load_known_athletes()
    candidates = build_search_candidates(db_athletes, known_athletes=known)

    # Run fuzzy search
    matches = fuzzy_search(q, candidates, limit=limit, threshold=threshold)

    return [
        AthleteSearchResult(
            id=m.athlete_id,
            display_name=m.display_name,
            appearance_count=m.appearance_count,
            similarity_score=m.similarity_score,
            matched_on=m.matched_on,
            source=m.source,
        )
        for m in matches
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
