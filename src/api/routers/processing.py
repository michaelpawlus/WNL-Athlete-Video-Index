"""API endpoints for video processing."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.api.dependencies import get_db
from src.database.schemas import ProcessVideoRequest, ProcessVideoResponse
from src.processing.pipeline import ProcessingPipeline, PipelineError

router = APIRouter(prefix="/processing", tags=["processing"])


@router.post("/video", response_model=ProcessVideoResponse)
def process_video(
    request: ProcessVideoRequest,
    db: Session = Depends(get_db),
):
    """Process a YouTube video to extract athlete appearances.

    This endpoint:
    1. Fetches the transcript from YouTube
    2. Uses Claude to extract athlete names and timestamps
    3. Stores the video and appearances in the database
    """
    pipeline = ProcessingPipeline(db=db)

    try:
        result = pipeline.process_video(
            url_or_id=request.url,
            title=request.title,
            event_name=request.event_name,
            event_date=request.event_date,
        )
    except PipelineError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if result.already_processed:
        return ProcessVideoResponse(
            video_id=result.video_id,
            youtube_id=result.youtube_id,
            athletes_found=result.athletes_found,
            appearances_created=result.appearances_created,
            message="Video was already processed",
        )

    return ProcessVideoResponse(
        video_id=result.video_id,
        youtube_id=result.youtube_id,
        athletes_found=result.athletes_found,
        appearances_created=result.appearances_created,
        message="Video processed successfully",
    )
