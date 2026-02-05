"""Shared dependencies for API endpoints."""
from typing import Generator

from sqlalchemy.orm import Session

from src.database.connection import SessionLocal


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
