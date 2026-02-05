"""Database connection and session management."""
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session

from src.config.settings import get_settings


def get_database_url() -> str:
    """Get database URL, ensuring data directory exists."""
    settings = get_settings()
    db_url = settings.database_url

    # Extract path from sqlite URL and ensure directory exists
    if db_url.startswith("sqlite:///"):
        db_path = db_url.replace("sqlite:///", "")
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    return db_url


# Create engine with SQLite-specific settings
engine = create_engine(
    get_database_url(),
    connect_args={"check_same_thread": False},  # Needed for SQLite with FastAPI
    echo=False,  # Set to True for SQL debugging
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """Dependency that provides a database session.

    Yields:
        SQLAlchemy Session that auto-closes after use
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
