"""Tests for LLM athlete extractor module."""
import pytest
from unittest.mock import Mock, patch, MagicMock

from src.processing.llm_extractor import (
    LLMAthleteExtractor,
    AthleteAppearance,
    ExtractionResult,
    LLMExtractorError,
)


class TestAthleteAppearance:
    """Tests for AthleteAppearance dataclass."""

    def test_appearance_creation(self):
        appearance = AthleteAppearance(
            name="John Smith", timestamp_seconds=120, confidence=0.95
        )
        assert appearance.name == "John Smith"
        assert appearance.timestamp_seconds == 120
        assert appearance.confidence == 0.95

    def test_confidence_validation_too_high(self):
        with pytest.raises(ValueError, match="Confidence must be between 0 and 1"):
            AthleteAppearance(name="Test", timestamp_seconds=0, confidence=1.5)

    def test_confidence_validation_too_low(self):
        with pytest.raises(ValueError, match="Confidence must be between 0 and 1"):
            AthleteAppearance(name="Test", timestamp_seconds=0, confidence=-0.1)

    def test_confidence_edge_cases(self):
        # Should not raise for exactly 0 or 1
        AthleteAppearance(name="Test", timestamp_seconds=0, confidence=0.0)
        AthleteAppearance(name="Test", timestamp_seconds=0, confidence=1.0)


class TestExtractionResult:
    """Tests for ExtractionResult dataclass."""

    def test_result_creation(self):
        appearances = [
            AthleteAppearance(name="John Smith", timestamp_seconds=15, confidence=0.9),
            AthleteAppearance(name="Sarah Johnson", timestamp_seconds=120, confidence=0.85),
        ]
        result = ExtractionResult(video_id="test123", appearances=appearances)

        assert result.video_id == "test123"
        assert len(result.appearances) == 2
        assert result.athlete_count == 2

    def test_athlete_count_with_duplicates(self):
        appearances = [
            AthleteAppearance(name="John Smith", timestamp_seconds=15, confidence=0.9),
            AthleteAppearance(name="John Smith", timestamp_seconds=30, confidence=0.8),
            AthleteAppearance(name="Sarah Johnson", timestamp_seconds=120, confidence=0.85),
        ]
        result = ExtractionResult(video_id="test123", appearances=appearances)

        # Should only count unique names
        assert result.athlete_count == 2

    def test_empty_appearances(self):
        result = ExtractionResult(video_id="test123", appearances=[])
        assert result.athlete_count == 0


class TestLLMAthleteExtractor:
    """Tests for LLMAthleteExtractor class."""

    def test_init_without_api_key_raises_error(self):
        with patch("src.processing.llm_extractor.get_settings") as mock_settings:
            mock_settings.return_value.anthropic_api_key = ""
            mock_settings.return_value.claude_model = "claude-sonnet-4-20250514"

            with pytest.raises(LLMExtractorError, match="API key not found"):
                LLMAthleteExtractor()

    @patch("src.processing.llm_extractor.Anthropic")
    @patch("src.processing.llm_extractor.get_settings")
    def test_init_with_api_key(self, mock_settings, mock_anthropic):
        mock_settings.return_value.anthropic_api_key = "test-key"
        mock_settings.return_value.claude_model = "claude-sonnet-4-20250514"

        extractor = LLMAthleteExtractor()

        assert extractor.api_key == "test-key"
        mock_anthropic.assert_called_once_with(api_key="test-key")

    @patch("src.processing.llm_extractor.Anthropic")
    @patch("src.processing.llm_extractor.get_settings")
    def test_init_with_custom_api_key(self, mock_settings, mock_anthropic):
        mock_settings.return_value.anthropic_api_key = "default-key"
        mock_settings.return_value.claude_model = "claude-sonnet-4-20250514"

        extractor = LLMAthleteExtractor(api_key="custom-key")

        assert extractor.api_key == "custom-key"
        mock_anthropic.assert_called_once_with(api_key="custom-key")

    @patch("src.processing.llm_extractor.Anthropic")
    @patch("src.processing.llm_extractor.get_settings")
    def test_extract_appearances_success(self, mock_settings, mock_anthropic):
        mock_settings.return_value.anthropic_api_key = "test-key"
        mock_settings.return_value.claude_model = "claude-sonnet-4-20250514"

        # Mock the tool use response
        mock_tool_use = Mock()
        mock_tool_use.type = "tool_use"
        mock_tool_use.input = {
            "appearances": [
                {"name": "John Smith", "timestamp_seconds": 15, "confidence": 0.95},
                {"name": "Sarah Johnson", "timestamp_seconds": 120, "confidence": 0.87},
            ]
        }

        mock_response = Mock()
        mock_response.content = [mock_tool_use]

        mock_client = Mock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.return_value = mock_client

        extractor = LLMAthleteExtractor()
        result = extractor.extract_appearances(
            "[00:15] Next up is John Smith\n[02:00] Now Sarah Johnson takes the stage",
            "video123",
        )

        assert result.video_id == "video123"
        assert len(result.appearances) == 2
        assert result.appearances[0].name == "John Smith"
        assert result.appearances[0].timestamp_seconds == 15
        assert result.appearances[0].confidence == 0.95
        assert result.appearances[1].name == "Sarah Johnson"

    @patch("src.processing.llm_extractor.Anthropic")
    @patch("src.processing.llm_extractor.get_settings")
    def test_extract_appearances_no_tool_use(self, mock_settings, mock_anthropic):
        mock_settings.return_value.anthropic_api_key = "test-key"
        mock_settings.return_value.claude_model = "claude-sonnet-4-20250514"

        # Mock response without tool use
        mock_text = Mock()
        mock_text.type = "text"

        mock_response = Mock()
        mock_response.content = [mock_text]

        mock_client = Mock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.return_value = mock_client

        extractor = LLMAthleteExtractor()

        with pytest.raises(LLMExtractorError, match="No tool use found"):
            extractor.extract_appearances("transcript text", "video123")

    @patch("src.processing.llm_extractor.Anthropic")
    @patch("src.processing.llm_extractor.get_settings")
    def test_extract_appearances_handles_malformed_entries(
        self, mock_settings, mock_anthropic
    ):
        mock_settings.return_value.anthropic_api_key = "test-key"
        mock_settings.return_value.claude_model = "claude-sonnet-4-20250514"

        # Mock response with some malformed entries
        mock_tool_use = Mock()
        mock_tool_use.type = "tool_use"
        mock_tool_use.input = {
            "appearances": [
                {"name": "John Smith", "timestamp_seconds": 15, "confidence": 0.95},
                {"name": "Bad Entry"},  # Missing required fields
                {"name": "Jane Doe", "timestamp_seconds": 60, "confidence": 1.5},  # Invalid confidence
            ]
        }

        mock_response = Mock()
        mock_response.content = [mock_tool_use]

        mock_client = Mock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.return_value = mock_client

        extractor = LLMAthleteExtractor()
        result = extractor.extract_appearances("transcript", "video123")

        # Should only have the valid entry
        assert len(result.appearances) == 1
        assert result.appearances[0].name == "John Smith"

    @patch("src.processing.llm_extractor.Anthropic")
    @patch("src.processing.llm_extractor.get_settings")
    def test_extract_appearances_empty_result(self, mock_settings, mock_anthropic):
        mock_settings.return_value.anthropic_api_key = "test-key"
        mock_settings.return_value.claude_model = "claude-sonnet-4-20250514"

        mock_tool_use = Mock()
        mock_tool_use.type = "tool_use"
        mock_tool_use.input = {"appearances": []}

        mock_response = Mock()
        mock_response.content = [mock_tool_use]

        mock_client = Mock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.return_value = mock_client

        extractor = LLMAthleteExtractor()
        result = extractor.extract_appearances("no athletes here", "video123")

        assert result.video_id == "video123"
        assert len(result.appearances) == 0
