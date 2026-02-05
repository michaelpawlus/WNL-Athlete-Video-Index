# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## Step 1 - Project Setup (2026-02-04)

### What was done:
- Created project structure with src/, tests/, scripts/, frontend/, data/ directories
- Configured Python dependencies in requirements.txt
- Set up Pydantic BaseSettings for environment management
- Created .env.example template and .gitignore

### Why these choices:
- **Pydantic Settings**: Type-safe configuration with automatic .env loading
- **SQLite**: Simple for MVP, file-based, upgradeable to PostgreSQL via SQLAlchemy
- **youtube-transcript-api**: No API key required, works with auto-captions
- **FastAPI**: Modern async Python web framework with automatic OpenAPI docs

---

## Step 2 - YouTube Transcript Fetcher (2026-02-04)

### What was done:
- Created TranscriptSegment dataclass for individual transcript segments with timing
- Created FetchedTranscript dataclass with full_text, text_with_timestamps, and duration properties
- Implemented TranscriptFetcher class to extract video IDs from various YouTube URL formats
- Added transcript fetching with preference for manual transcripts over auto-generated
- Created comprehensive test suite with 17 tests covering all functionality

### Why these choices:
- **Dataclasses**: Clean, typed data containers for transcript data
- **URL pattern matching**: Support youtube.com/watch, youtu.be, embed, and shorts URLs
- **Manual transcript preference**: Manual transcripts are typically more accurate than auto-generated
- **[MM:SS] timestamp format**: Human-readable format that LLMs can easily parse

---

## Step 3 - LLM Athlete Extractor (2026-02-04)

### What was done:
- Created prompt templates for ninja warrior competition context
- Implemented AthleteAppearance dataclass with confidence validation
- Created ExtractionResult dataclass with athlete counting
- Built LLMAthleteExtractor using Claude tool_use for structured output
- Added comprehensive test suite with 14 tests including edge cases

### Why these choices:
- **Claude tool_use**: Guarantees structured JSON output without parsing errors
- **Confidence scores**: Allow quality filtering at query time
- **System prompt with context**: Helps LLM distinguish competitors from commentators
- **Graceful handling of malformed entries**: Extraction continues even if some data is invalid

---

## Step 4 - Database Models (2026-02-04)

### What was done:
- Created SQLAlchemy ORM models: Athlete, Video, AthleteAppearance
- Implemented database connection with SQLite configuration
- Added Pydantic schemas for API request/response validation
- Created init_db.py script for database initialization
- Built test fixtures (conftest.py) and 13 database tests

### Why these choices:
- **SQLAlchemy ORM**: Type-safe database operations with relationship management
- **Cascade deletes**: Automatically clean up appearances when athlete/video deleted
- **JSON column for aliases**: Flexible storage for athlete name variations
- **Pydantic schemas**: Separate API models from database models for clean layering
- **raw_name_in_transcript**: Preserves original name for alias learning and debugging

---

## Step 5 - Processing Pipeline (2026-02-04)

### What was done:
- Created ProcessingPipeline class connecting transcript fetch, LLM extraction, and database storage
- Implemented idempotent processing (skip if already processed, force option available)
- Added athlete matching by name or alias (case-insensitive)
- Created process_video.py CLI script for command-line video processing
- Built 12 pipeline tests covering success, error, and edge cases

### Why these choices:
- **Idempotent processing**: Safe for batch operations, prevents duplicate records
- **Alias matching**: Handles variations in how commentators refer to athletes
- **CLI script**: Easy video processing without needing to run the full API
- **ProcessingResult dataclass**: Clean return type with all relevant info for callers

---

## Step 6 - FastAPI Application (2026-02-04)

### What was done:
- Created FastAPI app with CORS middleware for frontend access
- Implemented athlete search endpoint with partial name matching
- Added video listing and detail endpoints with appearance counts
- Built video processing endpoint for triggering pipeline via API
- Created 15 API tests covering all endpoints and edge cases

### Why these choices:
- **CORS enabled**: Allows frontend to call API from any origin (development mode)
- **Partial name search**: ILIKE pattern for user-friendly searching
- **Auto-generated docs**: /docs endpoint provides Swagger UI for API exploration
- **Dependency injection**: Database sessions managed via FastAPI dependencies
