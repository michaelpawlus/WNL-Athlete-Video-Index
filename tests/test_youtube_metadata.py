"""Tests for the YouTube metadata fetcher."""
import pytest
from datetime import datetime
from unittest.mock import patch, Mock

from src.processing.youtube_metadata import (
    YouTubeMetadataFetcher,
    YouTubeMetadata,
    parse_event_name_from_title,
    UPLOAD_DATE_RE,
)


class TestParseEventNameFromTitle:
    """Tests for parse_event_name_from_title helper."""

    def test_standard_title(self):
        assert parse_event_name_from_title("Sinai Sports - 12/21/25 - Tier 2 - Finals") == "Sinai Sports"

    def test_two_part_title(self):
        assert parse_event_name_from_title("My Gym - Session 1") == "My Gym"

    def test_no_separator(self):
        assert parse_event_name_from_title("Just A Simple Title") is None

    def test_empty_string(self):
        assert parse_event_name_from_title("") is None

    def test_none_input(self):
        assert parse_event_name_from_title(None) is None

    def test_leading_whitespace(self):
        assert parse_event_name_from_title("  Venue Name  - Date - Tier") == "Venue Name"


class TestUploadDateRegex:
    """Tests for the upload date regex pattern."""

    def test_matches_upload_date(self):
        html = '{"uploadDate":"2025-01-15","other":"stuff"}'
        match = UPLOAD_DATE_RE.search(html)
        assert match is not None
        assert match.group(1) == "2025-01-15"

    def test_matches_with_whitespace(self):
        html = '"uploadDate" : "2024-12-25"'
        match = UPLOAD_DATE_RE.search(html)
        assert match is not None
        assert match.group(1) == "2024-12-25"

    def test_no_match(self):
        html = "<html><body>no date here</body></html>"
        assert UPLOAD_DATE_RE.search(html) is None


class TestYouTubeMetadataFetcher:
    """Tests for YouTubeMetadataFetcher."""

    @patch("src.processing.youtube_metadata.httpx.get")
    def test_oembed_parsing(self, mock_get):
        """oEmbed response is parsed into metadata fields."""
        oembed_response = Mock()
        oembed_response.status_code = 200
        oembed_response.raise_for_status = Mock()
        oembed_response.json.return_value = {
            "title": "My Video Title",
            "author_name": "My Channel",
            "thumbnail_url": "https://i.ytimg.com/vi/abc123/hqdefault.jpg",
        }

        page_response = Mock()
        page_response.status_code = 200
        page_response.raise_for_status = Mock()
        page_response.text = '"uploadDate":"2025-06-15"'

        mock_get.side_effect = [oembed_response, page_response]

        fetcher = YouTubeMetadataFetcher()
        meta = fetcher.fetch("abc123")

        assert meta.video_id == "abc123"
        assert meta.title == "My Video Title"
        assert meta.channel_name == "My Channel"
        assert meta.thumbnail_url == "https://i.ytimg.com/vi/abc123/hqdefault.jpg"
        assert meta.upload_date == datetime(2025, 6, 15)

    @patch("src.processing.youtube_metadata.httpx.get")
    def test_graceful_failure_returns_empty_metadata(self, mock_get):
        """All network errors are swallowed; partial metadata returned."""
        mock_get.side_effect = Exception("network down")

        fetcher = YouTubeMetadataFetcher()
        meta = fetcher.fetch("abc123")

        assert meta.video_id == "abc123"
        assert meta.title is None
        assert meta.channel_name is None
        assert meta.upload_date is None
        assert meta.thumbnail_url is None

    @patch("src.processing.youtube_metadata.httpx.get")
    def test_oembed_fails_but_page_succeeds(self, mock_get):
        """If oEmbed fails, page scraping can still provide upload_date."""
        oembed_response = Mock()
        oembed_response.raise_for_status.side_effect = Exception("404")

        page_response = Mock()
        page_response.status_code = 200
        page_response.raise_for_status = Mock()
        page_response.text = '"uploadDate":"2025-03-10"'

        mock_get.side_effect = [oembed_response, page_response]

        fetcher = YouTubeMetadataFetcher()
        meta = fetcher.fetch("abc123")

        assert meta.title is None
        assert meta.upload_date == datetime(2025, 3, 10)

    @patch("src.processing.youtube_metadata.httpx.get")
    def test_page_has_no_upload_date(self, mock_get):
        """When page doesn't contain uploadDate, upload_date stays None."""
        oembed_response = Mock()
        oembed_response.status_code = 200
        oembed_response.raise_for_status = Mock()
        oembed_response.json.return_value = {
            "title": "Some Title",
            "author_name": "Channel",
        }

        page_response = Mock()
        page_response.status_code = 200
        page_response.raise_for_status = Mock()
        page_response.text = "<html>no structured data</html>"

        mock_get.side_effect = [oembed_response, page_response]

        fetcher = YouTubeMetadataFetcher()
        meta = fetcher.fetch("abc123")

        assert meta.title == "Some Title"
        assert meta.upload_date is None
