"""Tests for fuzzy search module."""
import pytest

from src.search.fuzzy import SearchCandidate, build_search_candidates, fuzzy_search


# --- Helpers ---

def make_db_athlete(id, name, aliases=None, count=1):
    return {
        "id": id,
        "display_name": name,
        "aliases": aliases or [],
        "appearance_count": count,
    }


def make_candidates(*athletes):
    """Build candidates from a list of db athlete dicts."""
    return build_search_candidates(athletes)


# --- build_search_candidates ---

class TestBuildSearchCandidates:
    def test_includes_display_name(self):
        candidates = make_candidates(make_db_athlete(1, "Esme"))
        assert len(candidates) == 1
        assert candidates[0].name == "Esme"
        assert candidates[0].athlete_id == 1

    def test_includes_aliases(self):
        candidates = make_candidates(
            make_db_athlete(1, "Kate", aliases=["Kate Feicht", "Kate Maley"])
        )
        names = [c.name for c in candidates]
        assert "Kate" in names
        assert "Kate Feicht" in names
        assert "Kate Maley" in names
        assert len(candidates) == 3

    def test_known_athletes_unlinked(self):
        known = [{"full_name": "Esme Newton-Pawlus", "first_name": "Esme", "db_athlete_id": None}]
        candidates = build_search_candidates([], known_athletes=known)
        assert len(candidates) == 1
        assert candidates[0].name == "Esme Newton-Pawlus"
        assert candidates[0].athlete_id is None
        assert candidates[0].source == "known"

    def test_known_athletes_linked_deduplicates(self):
        """Known athletes linked to a DB id already present should be skipped."""
        db = [make_db_athlete(1, "Esme", aliases=["Esme Newton-Pawlus"])]
        known = [{"full_name": "Esme Newton-Pawlus", "first_name": "Esme", "db_athlete_id": 1}]
        candidates = build_search_candidates(db, known_athletes=known)
        # Should have display_name + alias from DB, NOT the known duplicate
        names = [c.name for c in candidates]
        assert names.count("Esme Newton-Pawlus") == 1


# --- fuzzy_search ---

class TestFuzzySearch:
    def test_exact_match_scores_100(self):
        candidates = make_candidates(make_db_athlete(1, "Esme"))
        results = fuzzy_search("Esme", candidates)
        assert len(results) == 1
        assert results[0].similarity_score == 100

    def test_close_spelling_sloane_vs_sloan(self):
        candidates = make_candidates(make_db_athlete(13, "Sloan"))
        results = fuzzy_search("Sloane", candidates)
        assert len(results) == 1
        assert results[0].athlete_id == 13
        assert results[0].similarity_score > 80

    def test_partial_match_full_name_to_first(self):
        """'Esme Newton-Pawlus' should match 'Esme' via token_set_ratio."""
        candidates = make_candidates(make_db_athlete(1, "Esme"))
        results = fuzzy_search("Esme Newton-Pawlus", candidates)
        assert len(results) == 1
        assert results[0].athlete_id == 1
        assert results[0].similarity_score > 45

    def test_deduplication_by_athlete_id(self):
        """Same athlete matched via display_name and alias -> one result."""
        candidates = make_candidates(
            make_db_athlete(1, "Kate", aliases=["Kate Feicht"])
        )
        results = fuzzy_search("Kate", candidates)
        assert len(results) == 1
        assert results[0].athlete_id == 1
        # Should keep the highest scoring match
        assert results[0].similarity_score == 100

    def test_threshold_enforcement(self):
        candidates = make_candidates(make_db_athlete(1, "Esme"))
        results = fuzzy_search("ZZZZZ", candidates, threshold=45)
        assert len(results) == 0

    def test_limit_enforcement(self):
        athletes = [make_db_athlete(i, f"Athlete{i}") for i in range(20)]
        candidates = build_search_candidates(athletes)
        results = fuzzy_search("Athlete", candidates, limit=5)
        assert len(results) == 5

    def test_alias_match_shows_display_name(self):
        candidates = make_candidates(
            make_db_athlete(1, "Kate", aliases=["Kate Feicht"])
        )
        results = fuzzy_search("Kate Feicht", candidates)
        assert len(results) == 1
        assert results[0].display_name == "Kate"
        assert results[0].matched_on == "Kate Feicht"

    def test_known_unlinked_athlete_has_null_id(self):
        known = [{"full_name": "Brooklyn Schoon", "first_name": "Brooklyn", "db_athlete_id": None}]
        candidates = build_search_candidates([], known_athletes=known)
        results = fuzzy_search("Brooklyn", candidates)
        assert len(results) == 1
        assert results[0].athlete_id is None
        assert results[0].source == "known"
