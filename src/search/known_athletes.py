"""Loader for the known athletes registry (data/known_athletes.json)."""
import json
from functools import lru_cache
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parent.parent.parent / "data" / "known_athletes.json"


@lru_cache(maxsize=1)
def load_known_athletes():
    """Load and cache the known athletes list from JSON.

    Returns list of dicts: [{full_name, first_name, db_athlete_id}, ...]
    """
    if not DATA_FILE.exists():
        return []
    with open(DATA_FILE) as f:
        data = json.load(f)
    return data.get("athletes", [])


def save_known_athletes(athletes, meta=None):
    """Write athletes back to JSON (used by linking script).

    Clears the lru_cache so next load picks up changes.
    """
    if meta is None and DATA_FILE.exists():
        with open(DATA_FILE) as f:
            meta = json.load(f).get("meta", {})

    with open(DATA_FILE, "w") as f:
        json.dump({"meta": meta or {}, "athletes": athletes}, f, indent=2)
        f.write("\n")

    load_known_athletes.cache_clear()
