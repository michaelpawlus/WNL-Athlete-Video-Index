#!/usr/bin/env python3
"""Initialize the database by creating all tables."""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.database.connection import engine, Base
from src.database.models import Athlete, Video, AthleteAppearance


def init_database():
    """Create all database tables."""
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("Database initialized successfully!")

    # Print table info
    from sqlalchemy import inspect

    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print(f"\nCreated tables: {', '.join(tables)}")

    for table in tables:
        columns = inspector.get_columns(table)
        print(f"\n{table}:")
        for col in columns:
            print(f"  - {col['name']}: {col['type']}")


if __name__ == "__main__":
    init_database()
