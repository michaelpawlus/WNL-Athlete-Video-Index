"""Fuzzy search module for matching athlete names."""
from dataclasses import dataclass
from typing import Optional

from rapidfuzz import fuzz


@dataclass
class SearchCandidate:
    """A single searchable name entry."""

    name: str
    athlete_id: Optional[int]
    display_name: str
    source: str  # "db" or "known"
    appearance_count: int = 0


@dataclass
class FuzzyMatch:
    """A fuzzy search result."""

    athlete_id: Optional[int]
    display_name: str
    similarity_score: float
    matched_on: str
    source: str
    appearance_count: int = 0


def build_search_candidates(db_athletes, known_athletes=None):
    """Build a flat list of searchable name candidates.

    Args:
        db_athletes: List of dicts with keys: id, display_name, aliases, appearance_count
        known_athletes: Optional list of dicts with keys: full_name, first_name, db_athlete_id
    """
    candidates = []

    for athlete in db_athletes:
        athlete_id = athlete["id"]
        display_name = athlete["display_name"]
        appearance_count = athlete.get("appearance_count", 0)

        # Add display_name as candidate
        candidates.append(
            SearchCandidate(
                name=display_name,
                athlete_id=athlete_id,
                display_name=display_name,
                source="db",
                appearance_count=appearance_count,
            )
        )

        # Add each alias as candidate
        for alias in athlete.get("aliases", None) or []:
            candidates.append(
                SearchCandidate(
                    name=alias,
                    athlete_id=athlete_id,
                    display_name=display_name,
                    source="db",
                    appearance_count=appearance_count,
                )
            )

    if known_athletes:
        # Track which db_athlete_ids already have candidates
        db_ids = {c.athlete_id for c in candidates}

        for ka in known_athletes:
            db_id = ka.get("db_athlete_id")
            full_name = ka["full_name"]

            if db_id and db_id in db_ids:
                # Already covered via DB aliases — skip to avoid duplicates
                continue

            if db_id:
                # Known athlete linked to DB but not yet in candidates
                # (shouldn't happen after linking, but handle gracefully)
                appearance_count = 0
                for c in candidates:
                    if c.athlete_id == db_id:
                        appearance_count = c.appearance_count
                        break
                candidates.append(
                    SearchCandidate(
                        name=full_name,
                        athlete_id=db_id,
                        display_name=full_name,
                        source="known",
                        appearance_count=appearance_count,
                    )
                )
            else:
                # Unlinked known athlete
                candidates.append(
                    SearchCandidate(
                        name=full_name,
                        athlete_id=None,
                        display_name=full_name,
                        source="known",
                        appearance_count=0,
                    )
                )

    return candidates


def fuzzy_search(query, candidates, limit=10, threshold=45):
    """Score each candidate against query using multiple fuzzy strategies.

    Returns deduplicated results sorted by score descending.

    Args:
        query: Search string
        candidates: List of SearchCandidate
        limit: Max results to return
        threshold: Minimum score to include (0-100)
    """
    query_lower = query.lower()
    scored = []

    for candidate in candidates:
        name_lower = candidate.name.lower()

        # Use max of multiple strategies for best matching
        direct_ratio = fuzz.ratio(query_lower, name_lower)
        score = max(
            direct_ratio,
            fuzz.partial_ratio(query_lower, name_lower),
            fuzz.token_set_ratio(query_lower, name_lower),
        )

        if score >= threshold:
            scored.append((
                FuzzyMatch(
                    athlete_id=candidate.athlete_id,
                    display_name=candidate.display_name,
                    similarity_score=round(score, 1),
                    matched_on=candidate.name,
                    source=candidate.source,
                    appearance_count=candidate.appearance_count,
                ),
                direct_ratio,  # tiebreaker: prefer more specific name match
            ))

    # Deduplicate by athlete_id — keep highest score per athlete
    # On tie, prefer higher direct_ratio (more specific match)
    best_by_id = {}
    unlinked = []

    for match, direct in scored:
        if match.athlete_id is None:
            unlinked.append(match)
            continue

        existing = best_by_id.get(match.athlete_id)
        if existing is None:
            best_by_id[match.athlete_id] = (match, direct)
        elif match.similarity_score > existing[0].similarity_score:
            best_by_id[match.athlete_id] = (match, direct)
        elif match.similarity_score == existing[0].similarity_score and direct > existing[1]:
            best_by_id[match.athlete_id] = (match, direct)

    results = [m for m, _ in best_by_id.values()] + unlinked
    results.sort(key=lambda m: m.similarity_score, reverse=True)

    return results[:limit]
