"""FR11/FR13 step 2: resolve a free-text entity name extracted from a
question into a graph node (ADR-0004).

Reuses FR1's `search_entities` (`src/graph/queries.py`) rather than
reimplementing `rapidfuzz` matching a second time -- search and NL
resolution can then never disagree about what a name refers to. NL
resolution layers a *stricter* acceptance rule on top: ADR-0004's "confidently
resolve" means both a high absolute score and a clear margin over the
runner-up, matching ADR-0002's high-confidence bar for auto-resolving a name
reference with no human reviewing the match (unlike FR1's search results,
which a person scans before clicking).
"""

from __future__ import annotations

from dataclasses import dataclass

from src.graph.queries import EntityRef, search_entities
from src.graph.store import GraphStore

# ADR-0002's `DEFAULT_FUZZY_THRESHOLD` for auto-resolving a name-only
# cross-source reference with no human in the loop -- reused here for the
# same reason.
RESOLUTION_SCORE_THRESHOLD = 90.0
# The top candidate must beat the runner-up by at least this many points;
# otherwise two similarly-named entities (e.g. "Order Service" vs. "Order
# Management Service") are treated as ambiguous rather than silently
# guessing the higher-ranked one.
RESOLUTION_MARGIN = 10.0


@dataclass(frozen=True)
class ResolutionResult:
    entity: EntityRef | None
    # True only when `entity is None` because of a close-scoring tie, as
    # opposed to no candidate clearing the threshold at all -- the two cases
    # get different FR13 non-answer wording (`answering.py`).
    ambiguous: bool


def resolve_entity(store: GraphStore, name: str) -> ResolutionResult:
    """Resolves `name` to a single graph node, or reports that it couldn't
    be confidently resolved. Never returns a best-effort guess (FR13):
    `entity=None` always means "ask the user to be more specific," whether
    because nothing matched or because too much did.
    """
    candidates = search_entities(store, name, limit=5)
    if not candidates or candidates[0].score < RESOLUTION_SCORE_THRESHOLD:
        return ResolutionResult(entity=None, ambiguous=False)

    top = candidates[0]
    runner_up = candidates[1] if len(candidates) > 1 else None
    if runner_up is not None and (top.score - runner_up.score) < RESOLUTION_MARGIN:
        return ResolutionResult(entity=None, ambiguous=True)

    return ResolutionResult(
        entity=EntityRef(
            id=top.id,
            label=top.label,
            name=top.name,
            criticality=top.criticality,
            lifecycle_status=top.lifecycle_status,
        ),
        ambiguous=False,
    )
