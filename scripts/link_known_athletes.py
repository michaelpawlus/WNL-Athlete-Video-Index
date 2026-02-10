#!/usr/bin/env python3
"""Link known athletes to existing DB records via fuzzy matching.

For each known athlete, fuzzy-matches their first_name against DB display_names.
On match: sets db_athlete_id in JSON and adds full_name as alias on the DB record.

Usage:
    python scripts/link_known_athletes.py          # interactive mode
    python scripts/link_known_athletes.py --auto    # auto-confirm above threshold
"""
import argparse
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rapidfuzz import fuzz
from sqlalchemy.orm import Session

from src.database.connection import SessionLocal
from src.database.models import Athlete
from src.search.known_athletes import load_known_athletes, save_known_athletes


LINK_THRESHOLD = 85


def get_db_athletes(db: Session):
    """Load all athletes from DB."""
    return db.query(Athlete).all()


def find_best_match(first_name, db_athletes):
    """Find the best fuzzy match for a first name among DB athletes."""
    best_score = 0
    best_athlete = None

    for athlete in db_athletes:
        score = max(
            fuzz.ratio(first_name.lower(), athlete.display_name.lower()),
            fuzz.partial_ratio(first_name.lower(), athlete.display_name.lower()),
        )
        if score > best_score:
            best_score = score
            best_athlete = athlete

    return best_athlete, best_score


def link_athlete(db: Session, db_athlete: Athlete, full_name: str):
    """Add full_name as alias on the DB athlete record."""
    aliases = list(db_athlete.aliases or [])
    if full_name not in aliases:
        aliases.append(full_name)
        db_athlete.aliases = aliases
        db.commit()
        return True
    return False


def main():
    parser = argparse.ArgumentParser(description="Link known athletes to DB records")
    parser.add_argument("--auto", action="store_true", help="Auto-confirm matches above threshold")
    args = parser.parse_args()

    known = load_known_athletes()
    if not known:
        print("No known athletes found in data/known_athletes.json")
        return

    db = SessionLocal()
    try:
        db_athletes = get_db_athletes(db)
        if not db_athletes:
            print("No athletes in database. Process some videos first.")
            return

        print(f"Found {len(known)} known athletes, {len(db_athletes)} DB athletes\n")

        linked_count = 0
        skipped_count = 0

        for ka in known:
            full_name = ka["full_name"]
            first_name = ka["first_name"]

            if ka.get("db_athlete_id"):
                print(f"  [already linked] {full_name} -> DB id={ka['db_athlete_id']}")
                continue

            best_match, score = find_best_match(first_name, db_athletes)

            if best_match is None or score < LINK_THRESHOLD:
                print(f"  [no match] {full_name} (best: {best_match.display_name if best_match else 'none'}, score={score:.0f})")
                skipped_count += 1
                continue

            # Confirm link
            if args.auto:
                confirm = True
            else:
                answer = input(
                    f"  Link '{full_name}' -> '{best_match.display_name}' (id={best_match.id}, score={score:.0f})? [Y/n] "
                ).strip().lower()
                confirm = answer in ("", "y", "yes")

            if confirm:
                ka["db_athlete_id"] = best_match.id
                added = link_athlete(db, best_match, full_name)
                status = "alias added" if added else "alias exists"
                print(f"  [linked] {full_name} -> {best_match.display_name} (id={best_match.id}) [{status}]")
                linked_count += 1
            else:
                print(f"  [skipped] {full_name}")
                skipped_count += 1

        # Save updated known athletes JSON
        save_known_athletes(known)
        print(f"\nDone: {linked_count} linked, {skipped_count} skipped")

    finally:
        db.close()


if __name__ == "__main__":
    main()
