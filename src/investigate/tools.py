"""Allowlisted investigation tools wrapping GraphStore queries (`ADR-0007`).

No Text2Cypher. Adaptive tools must be invoked through `run_tool` so the
allowlist and budgets stay enforceable in tests.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from src.graph.queries import (
    DEFAULT_TRAVERSAL_DEPTH,
    MAX_TRAVERSAL_DEPTH,
    EntityRef,
    get_capability_rollup,
    get_dependency_paths,
    get_dependency_traversal,
    get_direct_capabilities,
    get_direct_dependencies,
    get_entity_detail,
    get_owning_team,
    get_ownership_rollup,
)
from src.graph.store import GraphStore
from src.investigate.config import agentic_max_traversal_depth
from src.investigate.models import InvestigationStep
from src.nlquery.answering import EvidenceDocChunk, EvidenceEdge
from src.nlquery.config import hybrid_doc_rag_enabled
from src.nlquery.doc_retrieve import retrieve_doc_chunks
from src.nlquery.resolution import resolve_entity
from src.retrieval.vector_store import RetrievedChunk

TOOL_NAMES = frozenset(
    {
        "traverse",
        "find_paths",
        "owners_rollup",
        "capabilities_rollup",
        "doc_search",
        "entity_detail",
    }
)


@dataclass
class EvidenceBundle:
    """Accumulated evidence available for citation gating."""

    edges: list[EvidenceEdge] = field(default_factory=list)
    docs: list[EvidenceDocChunk] = field(default_factory=list)
    entity_ids: set[str] = field(default_factory=set)
    node_names: dict[str, str] = field(default_factory=dict)
    _edge_keys: set[tuple[str, str, str]] = field(default_factory=set)
    _doc_keys: set[tuple[str, str]] = field(default_factory=set)

    def remember_entity(self, entity_id: str, name: str) -> None:
        self.entity_ids.add(entity_id)
        self.node_names[entity_id] = name

    def add_edge(self, edge: EvidenceEdge) -> None:
        key = (edge.source_id, edge.target_id, edge.rel_type)
        if key in self._edge_keys:
            return
        self._edge_keys.add(key)
        self.edges.append(edge)
        self.remember_entity(edge.source_id, edge.source_name)
        self.remember_entity(edge.target_id, edge.target_name)

    def add_doc(self, chunk: EvidenceDocChunk) -> None:
        key = (chunk.document_id, chunk.chunk_id)
        if key in self._doc_keys:
            return
        self._doc_keys.add(key)
        self.docs.append(chunk)

    def add_retrieved_chunk(self, chunk: RetrievedChunk) -> None:
        self.add_doc(
            EvidenceDocChunk(
                document_id=chunk.document_id,
                document_name=chunk.document_name,
                chunk_id=chunk.chunk_id,
                text=chunk.text,
                source_system=chunk.source_system,
                source_record_id=chunk.source_record_id,
            )
        )


def _rel_lookup(store: GraphStore) -> dict[tuple[str, str, str], dict]:
    return {
        (r["source_id"], r["target_id"], r["rel_type"]): r for r in store.get_all_relationships()
    }


def _edge_from_rel(
    store: GraphStore,
    source_id: str,
    target_id: str,
    rel_type: str,
    *,
    node_by_id: dict[str, dict] | None = None,
) -> EvidenceEdge | None:
    nodes = node_by_id or {n["id"]: n for n in store.get_all_nodes()}
    if source_id not in nodes or target_id not in nodes:
        return None
    rel = _rel_lookup(store).get((source_id, target_id, rel_type))
    return EvidenceEdge(
        source_id=source_id,
        source_name=nodes[source_id]["name"],
        rel_type=rel_type,
        target_id=target_id,
        target_name=nodes[target_id]["name"],
        source_system=(rel or {}).get("source_system", ""),
        source_record_id=(rel or {}).get("source_record_id", ""),
        evidence_type=(rel or {}).get("evidence_type", "documented"),
    )


def _ingest_direct_deps(
    bundle: EvidenceBundle, store: GraphStore, seed: EntityRef
) -> str:
    deps = get_direct_dependencies(store, seed.id)
    if deps is None:
        return "entity not found"
    count = 0
    for edge in deps.upstream:
        ev = _edge_from_rel(store, seed.id, edge.entity.id, edge.rel_type)
        if ev:
            bundle.add_edge(ev)
            count += 1
    for edge in deps.downstream:
        ev = _edge_from_rel(store, edge.entity.id, seed.id, edge.rel_type)
        if ev:
            bundle.add_edge(ev)
            count += 1
    return f"upstream={len(deps.upstream)} downstream={len(deps.downstream)} edges={count}"


def _ingest_traversal(
    bundle: EvidenceBundle,
    store: GraphStore,
    entity_id: str,
    direction: str,
    max_depth: int,
) -> str:
    if direction not in ("upstream", "downstream"):
        return "invalid direction"
    depth = max(1, min(int(max_depth), MAX_TRAVERSAL_DEPTH, agentic_max_traversal_depth()))
    result = get_dependency_traversal(store, entity_id, direction, max_depth=depth)  # type: ignore[arg-type]
    if result is None:
        return "entity not found"
    node_by_id = {n["id"]: n for n in store.get_all_nodes()}
    for node in result.nodes:
        bundle.remember_entity(node.entity.id, node.entity.name)
    added = 0
    for edge in result.edges:
        # Traversal edges are oriented as stored dependency edges.
        ev = _edge_from_rel(
            store, edge.source_id, edge.target_id, edge.rel_type, node_by_id=node_by_id
        )
        if ev:
            bundle.add_edge(ev)
            added += 1
    return f"direction={direction} depth={depth} nodes={len(result.nodes)} edges={added}"


def _ingest_owners(
    bundle: EvidenceBundle, store: GraphStore, entity_id: str, *, max_depth: int
) -> str:
    rollup = get_ownership_rollup(store, entity_id, direction="downstream", max_depth=max_depth)
    if rollup is None:
        return "entity not found"
    owner = get_owning_team(store, entity_id)
    node_by_id = {n["id"]: n for n in store.get_all_nodes()}
    if owner and entity_id in node_by_id:
        bundle.add_edge(
            EvidenceEdge(
                source_id=entity_id,
                source_name=node_by_id[entity_id]["name"],
                rel_type="OWNED_BY",
                target_id=owner.id,
                target_name=owner.name,
                source_system="team-ownership",
                evidence_type="documented",
            )
        )
    groups = 0
    for group in rollup.groups:
        if group.team is None:
            continue
        groups += 1
        for ent in group.entities:
            bundle.add_edge(
                EvidenceEdge(
                    source_id=ent.id,
                    source_name=ent.name,
                    rel_type="OWNED_BY",
                    target_id=group.team.id,
                    target_name=group.team.name,
                    source_system="team-ownership",
                    evidence_type="documented",
                )
            )
    return f"owner_groups={groups} seed_owner={owner.name if owner else 'none'}"


def _ingest_capabilities(
    bundle: EvidenceBundle, store: GraphStore, entity_id: str, *, max_depth: int
) -> str:
    caps = get_direct_capabilities(store, entity_id)
    rollup = get_capability_rollup(store, entity_id, direction="downstream", max_depth=max_depth)
    node_by_id = {n["id"]: n for n in store.get_all_nodes()}
    added = 0
    if caps:
        for cap in caps:
            # SUPPORTS is source tech → capability; find edge from store.
            for rel in store.get_all_relationships():
                if (
                    rel["rel_type"] == "SUPPORTS"
                    and rel["target_id"] == cap.id
                    and rel["source_id"] in node_by_id
                ):
                    # Prefer edges involving seed or known entities.
                    if rel["source_id"] == entity_id or rel["source_id"] in bundle.entity_ids:
                        ev = _edge_from_rel(
                            store, rel["source_id"], rel["target_id"], "SUPPORTS", node_by_id=node_by_id
                        )
                        if ev:
                            bundle.add_edge(ev)
                            added += 1
    if rollup:
        for group in rollup.groups:
            for ent in group.entities:
                ev = _edge_from_rel(
                    store, ent.id, group.capability.id, "SUPPORTS", node_by_id=node_by_id
                )
                if ev:
                    bundle.add_edge(ev)
                    added += 1
    return f"capability_edges={added}"


def run_skeleton(
    store: GraphStore,
    seed: EntityRef,
    question: str,
    *,
    bundle: EvidenceBundle | None = None,
    steps: list[InvestigationStep] | None = None,
) -> tuple[EvidenceBundle, list[InvestigationStep]]:
    """Required evidence gather — always runs before adaptive tools."""
    bundle = bundle or EvidenceBundle()
    steps = steps if steps is not None else []
    bundle.remember_entity(seed.id, seed.name)

    detail = get_entity_detail(store, seed.id)
    steps.append(
        InvestigationStep(
            phase="skeleton",
            tool="entity_detail",
            args_summary=f"id={seed.id}",
            result_summary=f"label={detail.label}" if detail else "missing",
        )
    )

    summary = _ingest_direct_deps(bundle, store, seed)
    steps.append(
        InvestigationStep(
            phase="skeleton",
            tool="direct_dependencies",
            args_summary=f"id={seed.id}",
            result_summary=summary,
        )
    )

    for direction in ("upstream", "downstream"):
        summary = _ingest_traversal(bundle, store, seed.id, direction, DEFAULT_TRAVERSAL_DEPTH)
        steps.append(
            InvestigationStep(
                phase="skeleton",
                tool="traverse",
                args_summary=f"id={seed.id} direction={direction} depth={DEFAULT_TRAVERSAL_DEPTH}",
                result_summary=summary,
            )
        )

    summary = _ingest_owners(bundle, store, seed.id, max_depth=DEFAULT_TRAVERSAL_DEPTH)
    steps.append(
        InvestigationStep(
            phase="skeleton",
            tool="owners_rollup",
            args_summary=f"id={seed.id} direction=downstream",
            result_summary=summary,
        )
    )

    summary = _ingest_capabilities(bundle, store, seed.id, max_depth=DEFAULT_TRAVERSAL_DEPTH)
    steps.append(
        InvestigationStep(
            phase="skeleton",
            tool="capabilities_rollup",
            args_summary=f"id={seed.id}",
            result_summary=summary,
        )
    )

    if hybrid_doc_rag_enabled():
        chunks = retrieve_doc_chunks(question)
        for chunk in chunks:
            bundle.add_retrieved_chunk(chunk)
        steps.append(
            InvestigationStep(
                phase="skeleton",
                tool="doc_search",
                args_summary=f"query={question[:60]!r}",
                result_summary=f"chunks={len(chunks)}",
            )
        )
    else:
        steps.append(
            InvestigationStep(
                phase="skeleton",
                tool="doc_search",
                args_summary="disabled",
                result_summary="hybrid_off",
            )
        )

    return bundle, steps


def run_tool(
    store: GraphStore,
    bundle: EvidenceBundle,
    name: str,
    args: dict,
    *,
    seed: EntityRef,
) -> str:
    """Execute one allowlisted adaptive tool. Raises ValueError if unknown."""
    if name not in TOOL_NAMES:
        raise ValueError(f"Tool {name!r} is not allowlisted")

    if name == "traverse":
        entity_id = str(args.get("entity_id") or seed.id)
        if entity_id not in bundle.entity_ids and entity_id != seed.id:
            return "refused: entity_id not in gathered evidence"
        direction = str(args.get("direction") or "downstream")
        depth = int(args.get("max_depth") or DEFAULT_TRAVERSAL_DEPTH)
        return _ingest_traversal(bundle, store, entity_id, direction, depth)

    if name == "find_paths":
        other_name = str(args.get("other_entity_name") or "").strip()
        if not other_name:
            return "missing other_entity_name"
        resolved = resolve_entity(store, other_name)
        if resolved.entity is None:
            return "other entity not found" if not resolved.ambiguous else "other entity ambiguous"
        other = resolved.entity
        bundle.remember_entity(other.id, other.name)
        paths = get_dependency_paths(store, seed.id, other.id)
        if paths is None or paths.shortest is None:
            return "no path"
        node_by_id = {n["id"]: n for n in store.get_all_nodes()}
        added = 0
        for path in [paths.shortest, *paths.alternates]:
            for edge in path.edges:
                ev = _edge_from_rel(
                    store,
                    edge.source_id,
                    edge.target_id,
                    edge.rel_type,
                    node_by_id=node_by_id,
                )
                if ev:
                    bundle.add_edge(ev)
                    added += 1
        return f"shortest_hops={paths.shortest.hops} path_edges={added}"

    if name == "owners_rollup":
        entity_id = str(args.get("entity_id") or seed.id)
        depth = int(args.get("max_depth") or DEFAULT_TRAVERSAL_DEPTH)
        return _ingest_owners(bundle, store, entity_id, max_depth=depth)

    if name == "capabilities_rollup":
        entity_id = str(args.get("entity_id") or seed.id)
        depth = int(args.get("max_depth") or DEFAULT_TRAVERSAL_DEPTH)
        return _ingest_capabilities(bundle, store, entity_id, max_depth=depth)

    if name == "doc_search":
        if not hybrid_doc_rag_enabled():
            return "hybrid_off"
        query = str(args.get("query") or "").strip()
        if not query:
            return "missing query"
        chunks = retrieve_doc_chunks(query)
        for chunk in chunks:
            bundle.add_retrieved_chunk(chunk)
        return f"chunks={len(chunks)}"

    if name == "entity_detail":
        entity_id = str(args.get("entity_id") or "").strip()
        if not entity_id:
            return "missing entity_id"
        if entity_id not in bundle.entity_ids and entity_id != seed.id:
            return "refused: entity_id not in gathered evidence"
        detail = get_entity_detail(store, entity_id)
        if detail is None:
            return "not found"
        bundle.remember_entity(detail.id, detail.name)
        return f"name={detail.name} label={detail.label}"

    raise ValueError(f"Unhandled tool {name!r}")
