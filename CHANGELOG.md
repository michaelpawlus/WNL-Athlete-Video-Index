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
