"""LLM-based athlete extraction using Claude API."""
from dataclasses import dataclass
from typing import Optional

from anthropic import Anthropic

from src.config.settings import get_settings
from .prompts import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE


@dataclass
class AthleteAppearance:
    """A single athlete appearance in a video."""

    name: str
    timestamp_seconds: int
    confidence: float

    def __post_init__(self):
        """Validate confidence is between 0 and 1."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be between 0 and 1, got {self.confidence}")


@dataclass
class ExtractionResult:
    """Result of extracting athlete appearances from a transcript."""

    video_id: str
    appearances: list[AthleteAppearance]

    @property
    def athlete_count(self) -> int:
        """Number of unique athletes found."""
        return len(set(a.name for a in self.appearances))


class LLMExtractorError(Exception):
    """Error during LLM extraction."""

    pass


class LLMAthleteExtractor:
    """Extracts athlete appearances from transcripts using Claude API."""

    # Tool definition for structured output
    EXTRACT_ATHLETES_TOOL = {
        "name": "record_athlete_appearances",
        "description": "Record all athlete appearances found in the transcript",
        "input_schema": {
            "type": "object",
            "properties": {
                "appearances": {
                    "type": "array",
                    "description": "List of athlete appearances found in the transcript",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "Full name of the athlete as mentioned in the transcript",
                            },
                            "timestamp_seconds": {
                                "type": "integer",
                                "description": "Timestamp in seconds when the athlete first appears/is introduced",
                            },
                            "confidence": {
                                "type": "number",
                                "description": "Confidence score between 0.0 and 1.0",
                                "minimum": 0.0,
                                "maximum": 1.0,
                            },
                        },
                        "required": ["name", "timestamp_seconds", "confidence"],
                    },
                },
            },
            "required": ["appearances"],
        },
    }

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """Initialize the extractor.

        Args:
            api_key: Anthropic API key (defaults to settings)
            model: Model to use (defaults to settings)
        """
        settings = get_settings()
        self.api_key = api_key or settings.anthropic_api_key
        self.model = model or settings.claude_model

        if not self.api_key:
            raise LLMExtractorError(
                "Anthropic API key not found. Set ANTHROPIC_API_KEY environment variable."
            )

        self.client = Anthropic(api_key=self.api_key)

    def extract_appearances(
        self, transcript_text: str, video_id: str
    ) -> ExtractionResult:
        """Extract athlete appearances from a transcript.

        Args:
            transcript_text: Transcript text with [MM:SS] timestamps
            video_id: YouTube video ID for reference

        Returns:
            ExtractionResult with list of AthleteAppearance objects

        Raises:
            LLMExtractorError: If extraction fails
        """
        user_prompt = USER_PROMPT_TEMPLATE.format(transcript=transcript_text)

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                tools=[self.EXTRACT_ATHLETES_TOOL],
                tool_choice={"type": "tool", "name": "record_athlete_appearances"},
                messages=[{"role": "user", "content": user_prompt}],
            )

            # Extract tool use from response
            tool_use = None
            for block in response.content:
                if block.type == "tool_use":
                    tool_use = block
                    break

            if not tool_use:
                raise LLMExtractorError("No tool use found in response")

            # Parse appearances from tool input
            appearances_data = tool_use.input.get("appearances", [])
            appearances = []

            for app_data in appearances_data:
                try:
                    appearance = AthleteAppearance(
                        name=app_data["name"],
                        timestamp_seconds=int(app_data["timestamp_seconds"]),
                        confidence=float(app_data["confidence"]),
                    )
                    appearances.append(appearance)
                except (KeyError, ValueError, TypeError) as e:
                    # Skip malformed entries but log them
                    continue

            return ExtractionResult(video_id=video_id, appearances=appearances)

        except Exception as e:
            if isinstance(e, LLMExtractorError):
                raise
            raise LLMExtractorError(f"Error calling Claude API: {e}")
