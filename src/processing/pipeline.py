"""Processing pipeline that connects transcript fetching, LLM extraction, and database storage."""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from src.database.models import Athlete, Video, AthleteAppearance
from .transcript_fetcher import TranscriptFetcher, TranscriptFetchError
from .llm_extractor import LLMAthleteExtractor, LLMExtractorError


@dataclass
class ProcessingResult:
    """Result of processing a video."""

    video_id: int
    youtube_id: str
    title: Optional[str]
    athletes_found: int
    appearances_created: int
    already_processed: bool = False
    error: Optional[str] = None


class PipelineError(Exception):
    """Error during pipeline processing."""

    pass


class ProcessingPipeline:
    """Pipeline for processing YouTube videos to extract athlete appearances."""

    def __init__(
        self,
        db: Session,
        transcript_fetcher: Optional[TranscriptFetcher] = None,
        llm_extractor: Optional[LLMAthleteExtractor] = None,
    ):
        """Initialize the pipeline.

        Args:
            db: SQLAlchemy database session
            transcript_fetcher: Optional custom transcript fetcher
            llm_extractor: Optional custom LLM extractor
        """
        self.db = db
        self.transcript_fetcher = transcript_fetcher or TranscriptFetcher()
        self.llm_extractor = llm_extractor or LLMAthleteExtractor()

    def process_video(
        self,
        url_or_id: str,
        title: Optional[str] = None,
        event_name: Optional[str] = None,
        event_date: Optional[datetime] = None,
        force_reprocess: bool = False,
    ) -> ProcessingResult:
        """Process a YouTube video to extract athlete appearances.

        This is the main entry point for the pipeline. It:
        1. Extracts the video ID from the URL
        2. Checks if already processed (idempotent)
        3. Fetches the transcript
        4. Extracts athletes via LLM
        5. Stores video and appearance records

        Args:
            url_or_id: YouTube URL or video ID
            title: Optional video title
            event_name: Optional event name
            event_date: Optional event date
            force_reprocess: If True, reprocess even if already done

        Returns:
            ProcessingResult with details about what was created

        Raises:
            PipelineError: If processing fails
        """
        # Step 1: Extract video ID
        try:
            video_id = self.transcript_fetcher.extract_video_id(url_or_id)
        except ValueError as e:
            raise PipelineError(f"Invalid video URL/ID: {e}")

        # Step 2: Check if already processed
        existing_video = self.db.query(Video).filter_by(youtube_id=video_id).first()
        if existing_video and not force_reprocess:
            return ProcessingResult(
                video_id=existing_video.id,
                youtube_id=video_id,
                title=existing_video.title,
                athletes_found=len(
                    set(a.athlete_id for a in existing_video.appearances)
                ),
                appearances_created=len(existing_video.appearances),
                already_processed=True,
            )

        # If force reprocessing, delete existing appearances
        if existing_video and force_reprocess:
            for appearance in existing_video.appearances:
                self.db.delete(appearance)
            self.db.commit()

        # Step 3: Fetch transcript
        try:
            transcript = self.transcript_fetcher.fetch(video_id)
        except TranscriptFetchError as e:
            raise PipelineError(f"Failed to fetch transcript: {e}")

        # Step 4: Extract athletes via LLM
        try:
            extraction = self.llm_extractor.extract_appearances(
                transcript.text_with_timestamps, video_id
            )
        except LLMExtractorError as e:
            raise PipelineError(f"Failed to extract athletes: {e}")

        # Step 5: Store video record
        if existing_video:
            video = existing_video
            video.title = title or video.title
            video.event_name = event_name or video.event_name
            video.event_date = event_date or video.event_date
            video.transcript_raw = transcript.text_with_timestamps
        else:
            video = Video(
                youtube_id=video_id,
                title=title,
                event_name=event_name,
                event_date=event_date,
                transcript_raw=transcript.text_with_timestamps,
            )
            self.db.add(video)

        self.db.commit()
        self.db.refresh(video)

        # Step 6: Create athlete and appearance records
        athletes_seen = set()
        appearances_created = 0

        for appearance_data in extraction.appearances:
            # Find or create athlete
            athlete = self._find_or_create_athlete(appearance_data.name)
            athletes_seen.add(athlete.id)

            # Create appearance record
            appearance = AthleteAppearance(
                athlete_id=athlete.id,
                video_id=video.id,
                timestamp_seconds=appearance_data.timestamp_seconds,
                confidence_score=appearance_data.confidence,
                raw_name_in_transcript=appearance_data.name,
            )
            self.db.add(appearance)
            appearances_created += 1

        self.db.commit()

        return ProcessingResult(
            video_id=video.id,
            youtube_id=video_id,
            title=title,
            athletes_found=len(athletes_seen),
            appearances_created=appearances_created,
        )

    def _find_or_create_athlete(self, name: str) -> Athlete:
        """Find an existing athlete by name or create a new one.

        Args:
            name: Athlete name to search for

        Returns:
            Existing or newly created Athlete
        """
        # Normalize the name for comparison
        normalized = name.strip().lower()

        # First, try exact match on display_name
        athlete = (
            self.db.query(Athlete)
            .filter(Athlete.display_name.ilike(normalized))
            .first()
        )
        if athlete:
            return athlete

        # Check aliases (JSON array search)
        all_athletes = self.db.query(Athlete).all()
        for athlete in all_athletes:
            if athlete.aliases:
                for alias in athlete.aliases:
                    if alias.lower() == normalized:
                        return athlete

        # Create new athlete
        athlete = Athlete(display_name=name.strip())
        self.db.add(athlete)
        self.db.commit()
        self.db.refresh(athlete)
        return athlete
