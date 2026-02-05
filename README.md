# WNL Athlete Video Index

A web application that allows users to search for ninja warrior athletes by name and receive timestamped links to their competition videos.

## Features

- **YouTube Transcript Extraction**: Automatically fetches transcripts from YouTube videos
- **AI-Powered Athlete Detection**: Uses Claude API to extract athlete names and timestamps
- **Searchable Database**: Find athletes by name with partial matching
- **Direct Video Links**: Click to jump directly to the moment an athlete appears

## Quick Start

### Prerequisites

- Python 3.10+
- Anthropic API key (for Claude)

### Installation

1. **Clone and enter the repository**:
   ```bash
   cd WNL-Athlete-Video-Index
   ```

2. **Create and activate a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env and add your ANTHROPIC_API_KEY
   ```

5. **Initialize the database**:
   ```bash
   python scripts/init_db.py
   ```

### Running the Application

1. **Start the API server**:
   ```bash
   uvicorn src.api.main:app --reload
   ```

2. **Open the frontend**:
   - Open `frontend/index.html` in your browser
   - Or serve it via a local server

3. **Access the API docs**:
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

## Processing Videos

### Via CLI

```bash
python scripts/process_video.py "YOUTUBE_URL" --title "Video Title" --event "Event Name"
```

Options:
- `--title`, `-t`: Video title
- `--event`, `-e`: Event name
- `--date`, `-d`: Event date (YYYY-MM-DD)
- `--force`, `-f`: Force reprocessing

### Via API

```bash
curl -X POST "http://localhost:8000/api/processing/video" \
  -H "Content-Type: application/json" \
  -d '{"url": "YOUTUBE_URL", "title": "Video Title"}'
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/athletes/search?q=name` | GET | Search athletes by name |
| `/api/athletes/{id}` | GET | Get athlete details with appearances |
| `/api/videos` | GET | List all processed videos |
| `/api/videos/{id}` | GET | Get video details with appearances |
| `/api/processing/video` | POST | Process a new video |
| `/health` | GET | Health check |

## Project Structure

```
WNL-Athlete-Video-Index/
├── src/
│   ├── config/          # Configuration and settings
│   ├── database/        # SQLAlchemy models and schemas
│   ├── processing/      # Transcript fetching and LLM extraction
│   └── api/             # FastAPI application
├── frontend/            # Static HTML/JS frontend
├── tests/               # Test suite
├── scripts/             # CLI utilities
└── data/                # SQLite database
```

## Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_transcript_fetcher.py -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

## Architecture

1. **Transcript Fetcher**: Extracts transcripts from YouTube using `youtube-transcript-api`
2. **LLM Extractor**: Uses Claude's tool_use feature to extract athlete names and timestamps
3. **Processing Pipeline**: Orchestrates fetching, extraction, and database storage
4. **FastAPI Backend**: REST API for searching and managing data
5. **Static Frontend**: Simple HTML/JS interface using Tailwind CSS

## Configuration

Environment variables (in `.env`):

| Variable | Description | Default |
|----------|-------------|---------|
| `ANTHROPIC_API_KEY` | Your Anthropic API key | (required) |
| `DATABASE_URL` | SQLite database path | `sqlite:///data/wnl_athlete_video_index.db` |
| `CLAUDE_MODEL` | Claude model to use | `claude-sonnet-4-20250514` |

## Development

### Adding New Features

1. Create a feature branch
2. Add tests for new functionality
3. Implement the feature
4. Run tests: `pytest tests/ -v`
5. Update documentation if needed

### Database Migrations

The project uses SQLAlchemy with SQLite. To reset the database:

```bash
rm data/wnl_athlete_video_index.db
python scripts/init_db.py
```

## Troubleshooting

### "No transcript available"
- The video may not have captions enabled
- Try a different video with captions

### "API key not found"
- Ensure `ANTHROPIC_API_KEY` is set in your `.env` file
- Check that the `.env` file is in the project root

### Frontend can't connect to API
- Ensure the API server is running on port 8000
- Check browser console for CORS errors
- Verify `API_BASE_URL` in `frontend/index.html`

## License

MIT License
