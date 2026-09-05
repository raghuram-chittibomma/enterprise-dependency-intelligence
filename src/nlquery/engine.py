"""FR11/FR13 step 3: dispatch a classified, entity-resolved question to the
*same* FR1-FR10 query template a structured route would use (ADR-0004) --
the retrieval half of the pipeline. `answering.py` (steps 4-5) is the only
piece that turns a `RetrievalResult` into text, so MVP2 can swap that one
piece for LLM-backed generation over the same retrieved data without
touching intent classification, entity resolution, or query dispatch here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from src.graph.queries import (
    CapabilityRollup,
    DirectDependencies,
    EntityRef,
    OwnershipRollup,
    PathSearchResult,
    get_capability_rollup,
    get_dependency_paths,
    get_direct_dependencies,
    get_ownership_rollup,
)
from src.graph.store import GraphStore
from src.nlquery.intent import LABEL_BY_TYPE_WORD, ParsedIntent, QuestionType, classify
from src.nlquery.resolution import resolve_entity

RetrievalStatus = Literal["ok", "unsupported", "not_found", "ambiguous"]

# Which of a `ParsedIntent.entities` keys name an actual entity to resolve
# via `resolve_entity` -- `owners_downstream`'s `entity_type` is a type word
# (e.g. "applications"), looked up in `LABEL_BY_TYPE_WORD` instead, never
# resolved as an entity name.
_ENTITY_KEYS: dict[QuestionType, tuple[str, ...]] = {
    "consumers_of": ("entity",),
    "depends_on": ("entity",),
    "owners_downstream": ("entity",),
    "capabilities_of": ("entity",),
    "path_between": ("source", "target"),
    "consumed_by": ("entity",),
    "used_by": ("entity",),
}

# Optional label filters for entity slots whose question shape only makes
# sense for certain node types. Without this, an exact-name collision
# between e.g. Application "Order Management" and BusinessCapability
# "Order Management" makes golden question 6 permanently FR13-ambiguous.
_ALLOWED_LABELS: dict[QuestionType, dict[str, frozenset[str]]] = {
    "consumed_by": {
        "entity": frozenset({"Application", "Service", "API"}),
    },
    "consumers_of": {
        "entity": frozenset({"API", "Service", "Application", "Database", "DataPipeline"}),
    },
    "used_by": {
        "entity": frozenset({"Database", "API", "Service", "DataPipeline", "ExternalSystem"}),
    },
}


@dataclass(frozen=True)
class SubgraphEdge:
    """One edge in an open-ended Graph RAG retrieval subgraph (MVP2),
    carrying ADR-0003 provenance for FR12/FR15 citation checks.
    """

    source_id: str
    source_name: str
    rel_type: str
    target_id: str
    target_name: str
    source_system: str
    source_record_id: str
    evidence_type: str


@dataclass(frozen=True)
class RetrievalResult:
    question: str
    question_type: QuestionType | None
    status: RetrievalStatus
    # Set only for `not_found`/`ambiguous`: the raw name text that failed to
    # resolve, for the FR13 non-answer message.
    unresolved_name: str | None = None
    # Every entity resolved from the question, keyed the same as
    # `ParsedIntent.entities` (minus any non-entity keys like `entity_type`).
    resolved: dict[str, EntityRef] | None = None
    # `owners_downstream`'s recognized label filter (e.g. "Application"),
    # or `None` if the question's type word wasn't recognized.
    type_filter: str | None = None
    direct_dependencies: DirectDependencies | None = None
    ownership_rollup: OwnershipRollup | None = None
    capability_rollup: CapabilityRollup | None = None
    path_result: PathSearchResult | None = None
    # MVP2 open-ended Graph RAG (`ADR-0005`): set when retrieval came from
    # `retrieve_open_ended` rather than a closed template dispatch.
    open_ended: bool = False
    open_subgraph_nodes: list[EntityRef] | None = None
    open_subgraph_edges: list[SubgraphEdge] | None = None


def _resolve_entities(
    store: GraphStore, intent: ParsedIntent
) -> tuple[dict[str, EntityRef], str | None, bool]:
    """Resolves every entity-name key in `intent.entities`, in order.
    Returns `(resolved, failed_name, ambiguous)`: on the first name that
    can't be confidently resolved, resolution stops early and that name is
    returned as `failed_name` (so e.g. `path_between` never bothers
    resolving `target` if `source` already failed).
    """
    resolved: dict[str, EntityRef] = {}
    label_filters = _ALLOWED_LABELS.get(intent.question_type, {})
    for key in _ENTITY_KEYS[intent.question_type]:
        raw_name = intent.entities[key]
        result = resolve_entity(store, raw_name, allowed_labels=label_filters.get(key))
        if result.entity is None:
            return resolved, raw_name, result.ambiguous
        resolved[key] = result.entity
    return resolved, None, False


def retrieve(store: GraphStore, question: str) -> RetrievalResult:
    """FR11 steps 1-3: classify, resolve, dispatch. Never raises -- every
    failure mode is a `RetrievalResult.status` value, per FR13's "always an
    explicit non-answer" contract.
    """
    intent = classify(question)
    if intent is None:
        return RetrievalResult(question=question, question_type=None, status="unsupported")

    resolved, failed_name, ambiguous = _resolve_entities(store, intent)
    if failed_name is not None:
        return RetrievalResult(
            question=question,
            question_type=intent.question_type,
            status="ambiguous" if ambiguous else "not_found",
            unresolved_name=failed_name,
        )

    match intent.question_type:
        case "depends_on" | "consumers_of" | "consumed_by" | "used_by":
            # All four questions are "one hop over the FR3 dependency edges
            # around a single entity" -- they differ only in which
            # direction/rel_type/label `answering.py` filters for, not in
            # the query itself.
            deps = get_direct_dependencies(store, resolved["entity"].id)
            return RetrievalResult(
                question=question,
                question_type=intent.question_type,
                status="ok",
                resolved=resolved,
                direct_dependencies=deps,
            )
        case "owners_downstream":
            rollup = get_ownership_rollup(store, resolved["entity"].id, "downstream")
            type_filter = LABEL_BY_TYPE_WORD.get(intent.entities["entity_type"].lower())
            return RetrievalResult(
                question=question,
                question_type=intent.question_type,
                status="ok",
                resolved=resolved,
                ownership_rollup=rollup,
                type_filter=type_filter,
            )
        case "capabilities_of":
            rollup = get_capability_rollup(store, resolved["entity"].id, "downstream")
            return RetrievalResult(
                question=question,
                question_type=intent.question_type,
                status="ok",
                resolved=resolved,
                capability_rollup=rollup,
            )
        case "path_between":
            path_result = get_dependency_paths(store, resolved["source"].id, resolved["target"].id)
            return RetrievalResult(
                question=question,
                question_type=intent.question_type,
                status="ok",
                resolved=resolved,
                path_result=path_result,
            )
        case _:
            # Unreachable: `_ENTITY_KEYS`/`classify()` only ever produce the
            # 7 `QuestionType` values, all matched above.
            raise AssertionError(f"unhandled question type: {intent.question_type!r}")
