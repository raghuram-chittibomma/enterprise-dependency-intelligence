"""MVP2 open-ended Graph RAG retrieval (`ADR-0005`).

No LLM here: resolve entity mentions in the question text against the
graph, then assemble a bounded dependency subgraph (plus ownership /
capability edges touching those nodes) for `LLMAnswerGenerator` to ground
against.
"""

from __future__ import annotations

from src.graph.queries import (
    DEFAULT_TRAVERSAL_DEPTH,
    DEPENDENCY_REL_TYPES,
    EntityRef,
    get_dependency_traversal,
)
from src.graph.store import GraphStore
from src.nlquery.engine import RetrievalResult, SubgraphEdge
from src.nlquery.resolution import resolve_entity


def _mention_candidates(question: str, nodes: list[dict]) -> list[str]:
    """Return distinct node names that appear as substrings of `question`,
    longest names first so "Customer API v1" wins over "Customer".
    """
    lowered = question.lower()
    names = sorted({n["name"] for n in nodes if n.get("name")}, key=len, reverse=True)
    found: list[str] = []
    occupied: list[tuple[int, int]] = []
    for name in names:
        needle = name.lower()
        if len(needle) < 3:
            continue
        start = lowered.find(needle)
        if start < 0:
            continue
        end = start + len(needle)
        if any(start < o_end and end > o_start for o_start, o_end in occupied):
            continue
        occupied.append((start, end))
        found.append(name)
    return found


def _entity_ref(node: dict) -> EntityRef:
    return EntityRef(
        id=node["id"],
        label=node["label"],
        name=node["name"],
        criticality=node.get("criticality"),
        lifecycle_status=node.get("lifecycle_status", "active"),
    )


def retrieve_open_ended(
    store: GraphStore,
    question: str,
    *,
    max_depth: int = DEFAULT_TRAVERSAL_DEPTH,
) -> RetrievalResult:
    """Build an open-ended retrieval result for Graph RAG generation.

    Returns `status=not_found` when no entity mention resolves; `ok` with a
    (possibly empty-of-edges) subgraph when at least one seed entity is
    found. Never classifies intent — caller only invokes this after MVP1
    `classify()` returned None.
    """
    nodes = store.get_all_nodes()
    node_by_id = {n["id"]: n for n in nodes}
    mention_names = _mention_candidates(question, nodes)

    seeds: list[EntityRef] = []
    seen_ids: set[str] = set()
    for name in mention_names:
        result = resolve_entity(store, name)
        if result.entity is None or result.ambiguous or result.entity.id in seen_ids:
            continue
        seeds.append(result.entity)
        seen_ids.add(result.entity.id)

    # Fallback: if substring scan found nothing, try the whole question as
    # a single fuzzy name (helps short prompts like "Tell me about Storefront").
    if not seeds:
        stripped = question.strip().rstrip("?")
        result = resolve_entity(store, stripped)
        if (
            result.entity is not None
            and not result.ambiguous
            and result.entity.name.lower() in stripped.lower()
        ):
            seeds.append(result.entity)

    if not seeds:
        return RetrievalResult(
            question=question,
            question_type=None,
            status="not_found",
            unresolved_name=question.strip()[:80] or "the question",
            open_ended=True,
        )

    seed_ids = {s.id for s in seeds}
    reached_ids: set[str] = set(seed_ids)
    for seed in seeds:
        for direction in ("upstream", "downstream"):
            traversal = get_dependency_traversal(store, seed.id, direction, max_depth=max_depth)
            if traversal is None:
                continue
            for node in traversal.nodes:
                reached_ids.add(node.entity.id)

    # Dependency edges between reached nodes, plus OWNED_BY / SUPPORTS that
    # touch a reached node (so ownership/capability questions have evidence).
    edge_keys: set[tuple[str, str, str]] = set()
    edges: list[SubgraphEdge] = []
    for rel in store.get_all_relationships():
        source_id, target_id = rel["source_id"], rel["target_id"]
        rel_type = rel["rel_type"]
        if source_id not in node_by_id or target_id not in node_by_id:
            continue
        include = False
        if rel_type in DEPENDENCY_REL_TYPES:
            include = source_id in reached_ids and target_id in reached_ids
        elif rel_type in {"OWNED_BY", "SUPPORTS"}:
            include = source_id in reached_ids or target_id in reached_ids
            if include:
                reached_ids.add(source_id)
                reached_ids.add(target_id)
        if not include:
            continue
        key = (source_id, target_id, rel_type)
        if key in edge_keys:
            continue
        edge_keys.add(key)
        edges.append(
            SubgraphEdge(
                source_id=source_id,
                source_name=node_by_id[source_id]["name"],
                rel_type=rel_type,
                target_id=target_id,
                target_name=node_by_id[target_id]["name"],
                source_system=rel.get("source_system", ""),
                source_record_id=rel.get("source_record_id", ""),
                evidence_type=rel.get("evidence_type", "documented"),
            )
        )

    subgraph_nodes = [
        _entity_ref(node_by_id[node_id])
        for node_id in sorted(reached_ids, key=lambda i: node_by_id[i]["name"])
        if node_id in node_by_id
    ]
    edges.sort(key=lambda e: (e.rel_type, e.source_name, e.target_name))

    resolved = {f"seed_{i}": seed for i, seed in enumerate(seeds)}
    # Keep a stable "entity" key for the first seed for logging convenience.
    resolved["entity"] = seeds[0]

    return RetrievalResult(
        question=question,
        question_type=None,
        status="ok",
        resolved=resolved,
        open_ended=True,
        open_subgraph_nodes=subgraph_nodes,
        open_subgraph_edges=edges,
    )


__all__ = ["retrieve_open_ended"]
