"""YouTube transcript fetching module."""
import re
from dataclasses import dataclass
from typing import Optional

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    NoTranscriptFound,
    TranscriptsDisabled,
    VideoUnavailable,
)


@dataclass
class TranscriptSegment:
    """A single segment of a transcript with timing information."""

    text: str
    start: float
    duration: float

    @property
    def end(self) -> float:
        """End time of the segment in seconds."""
        return self.start + self.duration


@dataclass
class FetchedTranscript:
    """Complete transcript with metadata."""

    video_id: str
    segments: list[TranscriptSegment]
    language: str
    is_auto_generated: bool

    @property
    def full_text(self) -> str:
        """Full transcript text without timestamps."""
        return " ".join(segment.text for segment in self.segments)

    @property
    def text_with_timestamps(self) -> str:
        """Transcript with [MM:SS] timestamps for LLM processing."""
        lines = []
        for segment in self.segments:
            minutes = int(segment.start // 60)
            seconds = int(segment.start % 60)
            timestamp = f"[{minutes:02d}:{seconds:02d}]"
            lines.append(f"{timestamp} {segment.text}")
        return "\n".join(lines)

    @property
    def duration_seconds(self) -> float:
        """Total duration of the transcript in seconds."""
        if not self.segments:
            return 0.0
        last_segment = self.segments[-1]
        return last_segment.start + last_segment.duration


class TranscriptFetchError(Exception):
    """Error fetching transcript from YouTube."""

    pass


class TranscriptFetcher:
    """Fetches transcripts from YouTube videos."""

    # Patterns to extract video ID from various URL formats
    VIDEO_ID_PATTERNS = [
        # Standard watch URL: youtube.com/watch?v=VIDEO_ID
        r"(?:youtube\.com/watch\?.*v=)([a-zA-Z0-9_-]{11})",
        # Short URL: youtu.be/VIDEO_ID
        r"(?:youtu\.be/)([a-zA-Z0-9_-]{11})",
        # Embed URL: youtube.com/embed/VIDEO_ID
        r"(?:youtube\.com/embed/)([a-zA-Z0-9_-]{11})",
        # Shorts URL: youtube.com/shorts/VIDEO_ID
        r"(?:youtube\.com/shorts/)([a-zA-Z0-9_-]{11})",
        # Just the video ID
        r"^([a-zA-Z0-9_-]{11})$",
    ]

    def extract_video_id(self, url_or_id: str) -> str:
        """Extract video ID from URL or return if already an ID.

        Args:
            url_or_id: YouTube URL or video ID

        Returns:
            11-character video ID

        Raises:
            ValueError: If no valid video ID can be extracted
        """
        url_or_id = url_or_id.strip()

        for pattern in self.VIDEO_ID_PATTERNS:
            match = re.search(pattern, url_or_id)
            if match:
                return match.group(1)

        raise ValueError(f"Could not extract video ID from: {url_or_id}")

    def fetch(
        self, url_or_id: str, languages: Optional[list[str]] = None
    ) -> FetchedTranscript:
        """Fetch transcript for a YouTube video.

        Args:
            url_or_id: YouTube URL or video ID
            languages: Preferred languages, defaults to ["en"]

        Returns:
            FetchedTranscript with segments and metadata

        Raises:
            TranscriptFetchError: If transcript cannot be fetched
        """
        if languages is None:
            languages = ["en"]

        video_id = self.extract_video_id(url_or_id)

        try:
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

            # Try to find a manually created transcript first
            transcript = None
            is_auto_generated = False

            try:
                transcript = transcript_list.find_manually_created_transcript(languages)
            except NoTranscriptFound:
                # Fall back to auto-generated
                try:
                    transcript = transcript_list.find_generated_transcript(languages)
                    is_auto_generated = True
                except NoTranscriptFound:
                    # Try to get any available transcript
                    try:
                        transcript = transcript_list.find_transcript(languages)
                        is_auto_generated = transcript.is_generated
                    except NoTranscriptFound:
                        raise TranscriptFetchError(
                            f"No transcript available in {languages} for video {video_id}"
                        )

            # Fetch the transcript data
            transcript_data = transcript.fetch()

            segments = [
                TranscriptSegment(
                    text=entry["text"],
                    start=entry["start"],
                    duration=entry["duration"],
                )
                for entry in transcript_data
            ]

            return FetchedTranscript(
                video_id=video_id,
                segments=segments,
                language=transcript.language_code,
                is_auto_generated=is_auto_generated,
            )

        except TranscriptsDisabled:
            raise TranscriptFetchError(
                f"Transcripts are disabled for video {video_id}"
            )
        except VideoUnavailable:
            raise TranscriptFetchError(f"Video {video_id} is unavailable")
        except Exception as e:
            raise TranscriptFetchError(f"Error fetching transcript: {e}")
