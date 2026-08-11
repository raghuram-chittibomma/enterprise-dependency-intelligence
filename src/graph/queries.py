"""Read-only query templates implementing FR1-FR10 and FR12 (see
`docs/00_project/PRODUCT_BRIEF.md`), growing one FR at a time. Each function
takes a `GraphStore` and plain arguments and returns plain dataclasses --
no framework (FastAPI/Jinja2) types leak in here, so these are reusable by
both the structured routes and the NL query layer (`src/nlquery/`, per
`ARCHITECTURE.md`'s "thin front-end over the same templates" design).
"""

from __future__ import annotations

from dataclasses import dataclass

from rapidfuzz import fuzz

from src.graph.store import GraphStore

# Below this score (0-100), a name is considered an unrelated result rather
# than a plausible typo/reordering -- deliberately looser than ADR-0002's
# entity-resolution threshold, since search is a ranked, human-reviewed
# list (FR1), not an auto-accept decision. Tuned against the real
# generated dataset (see `tests/unit/test_queries.py`): true typo/reorder
# matches score >=71 there, unrelated names top out at <=67.
MIN_SEARCH_SCORE = 68
EXACT_MATCH_SCORE = 100.0
SUBSTRING_MATCH_SCORE = 95.0


@dataclass(frozen=True)
class SearchResult:
    id: str
    label: str
    name: str
    description: str
    lifecycle_status: str
    criticality: str | None
    score: float


def _per_word_alignment_score(query_words: list[str], name_words: list[str]) -> float:
    """The *worst*-matching query word's best available match among the
    name's words. Taking the min (not average/max) across query words means
    every query word must find some decent counterpart in the name --
    otherwise a query like "Custmer API" would partially match an unrelated
    name like "Customer Portal" purely on the "Custmer"/"Customer" word
    pair, ignoring that "API" doesn't match "Portal" at all.
    """
    if not query_words or not name_words:
        return 0.0
    return min(
        max(fuzz.ratio(query_word, name_word) for name_word in name_words)
        for query_word in query_words
    )


def _fuzzy_score(query: str, name: str) -> float:
    query_words = query.split()
    # Plain whole-string ratio is only a reliable signal for single-word
    # queries; for multi-word queries it can score coincidentally high
    # against an unrelated name that merely shares letters in similar
    # positions (e.g. "Custmer API" vs "Customer Portal" scores 69 on
    # `ratio` alone), so a token-order-invariant comparison is used
    # instead once there's more than one word to align.
    whole_score = (
        fuzz.ratio(query, name) if len(query_words) == 1 else fuzz.token_sort_ratio(query, name)
    )
    return max(whole_score, _per_word_alignment_score(query_words, name.split()))


def _score_name(query: str, name: str) -> float:
    normalized_query, normalized_name = query.lower(), name.lower()
    if normalized_query == normalized_name:
        return EXACT_MATCH_SCORE
    if normalized_query in normalized_name:
        return SUBSTRING_MATCH_SCORE
    return _fuzzy_score(query, name)


def search_entities(store: GraphStore, query: str, limit: int = 20) -> list[SearchResult]:
    """FR1: fuzzy-match entity search by name, across every node type.

    MVP1's graph is small enough (tens of nodes) that fetching everything
    and ranking in-process is simpler and just as fast as backend-specific
    full-text search, and it keeps this function identical for both the
    Neo4j and fallback stores.
    """
    normalized_query = query.strip()
    if not normalized_query:
        return []

    scored = [
        (score, node)
        for node in store.get_all_nodes()
        if (score := _score_name(normalized_query, node["name"])) >= MIN_SEARCH_SCORE
    ]
    scored.sort(key=lambda pair: (-pair[0], pair[1]["name"]))
    return [
        SearchResult(
            id=node["id"],
            label=node["label"],
            name=node["name"],
            description=node.get("description", ""),
            lifecycle_status=node.get("lifecycle_status", "active"),
            criticality=node.get("criticality"),
            score=score,
        )
        for score, node in scored[:limit]
    ]
