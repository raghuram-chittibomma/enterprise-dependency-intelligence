"""Read-only query templates implementing FR1-FR10 and FR12 (see
`docs/00_project/PRODUCT_BRIEF.md`), growing one FR at a time. Each function
takes a `GraphStore` and plain arguments and returns plain dataclasses --
no framework (FastAPI/Jinja2) types leak in here, so these are reusable by
both the structured routes and the NL query layer (`src/nlquery/`, per
`ARCHITECTURE.md`'s "thin front-end over the same templates" design).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from rapidfuzz import fuzz

from src.graph.store import GraphStore

TraversalDirection = Literal["upstream", "downstream"]

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


@dataclass(frozen=True)
class OwnerRef:
    id: str
    name: str


# Fields common to every node (ontology's `NodeBase`, see DATA_MODEL.md) --
# everything else on a node dict is a type-specific property (e.g.
# `technology`/`environment` on Application, `engine` on Database) that
# `get_entity_detail` surfaces generically via `EntityDetail.properties`
# rather than a per-type dataclass, since FR2 must render all 9 node types.
_COMMON_NODE_FIELDS = frozenset(
    {
        "id",
        "label",
        "name",
        "description",
        "lifecycle_status",
        "criticality",
        "source_system",
        "source_record_id",
        "ingested_at",
    }
)


@dataclass(frozen=True)
class EntityDetail:
    id: str
    label: str
    name: str
    description: str
    lifecycle_status: str
    criticality: str | None
    owner: OwnerRef | None
    properties: dict[str, object]
    source_system: str
    source_record_id: str
    ingested_at: str


# The 4 relationship types that represent an actual functional dependency
# (DATA_MODEL.md: "`DEPENDS_ON` is intentionally never persisted" -- FR3's
# upstream/downstream is answered by traversing these instead). OWNED_BY
# (ownership), SUPPORTS (business-capability), and REPLACED_BY (lifecycle)
# are deliberately excluded -- they're real edges, just not *dependency*
# edges.
DEPENDENCY_REL_TYPES = frozenset({"CONSUMES", "READS_FROM", "WRITES_TO", "INTEGRATES_WITH"})


def _dependency_relationships(store: GraphStore) -> list[dict]:
    """The dependency-only subset of relationships (`DEPENDENCY_REL_TYPES`),
    shared by FR3 (direct deps), FR4/FR5 (traversal), and FR6/FR7 (paths) --
    every one of these features answers "how does A connect to B" over the
    same substrate, just with a different traversal shape on top.
    """
    return [rel for rel in store.get_all_relationships() if rel["rel_type"] in DEPENDENCY_REL_TYPES]


@dataclass(frozen=True)
class EntityRef:
    """A lightweight reference to another entity -- enough to render a
    linked badge/name in a list (search results, dependency lists, ...)
    without pulling in that entity's full detail.
    """

    id: str
    label: str
    name: str
    criticality: str | None
    lifecycle_status: str


@dataclass(frozen=True)
class DependencyEdge:
    entity: EntityRef
    rel_type: str


@dataclass(frozen=True)
class DirectDependencies:
    upstream: list[DependencyEdge]  # entities this entity depends on (outbound)
    downstream: list[DependencyEdge]  # entities that depend on this entity (inbound)


def _entity_ref(node: dict) -> EntityRef:
    return EntityRef(
        id=node["id"],
        label=node["label"],
        name=node["name"],
        criticality=node.get("criticality"),
        lifecycle_status=node.get("lifecycle_status", "active"),
    )


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


def get_entity_detail(store: GraphStore, entity_id: str) -> EntityDetail | None:
    """FR2: full metadata for a single entity, including its owning team
    (a simple single-hop lookup -- the multi-entity ownership *rollup* over
    a whole dependency subtree is FR9/increment-11, a separate function).
    Returns `None` if `entity_id` doesn't match any node (the route turns
    this into a 404).
    """
    nodes = store.get_all_nodes()
    node = next((n for n in nodes if n["id"] == entity_id), None)
    if node is None:
        return None

    owner = None
    for rel in store.get_all_relationships():
        if rel["rel_type"] == "OWNED_BY" and rel["source_id"] == entity_id:
            owner_node = next((n for n in nodes if n["id"] == rel["target_id"]), None)
            if owner_node is not None:
                owner = OwnerRef(id=owner_node["id"], name=owner_node["name"])
            break

    properties = {k: v for k, v in node.items() if k not in _COMMON_NODE_FIELDS}

    return EntityDetail(
        id=node["id"],
        label=node["label"],
        name=node["name"],
        description=node.get("description", ""),
        lifecycle_status=node.get("lifecycle_status", "active"),
        criticality=node.get("criticality"),
        owner=owner,
        properties=properties,
        source_system=node["source_system"],
        source_record_id=node["source_record_id"],
        ingested_at=str(node.get("ingested_at", "")),
    )


def get_direct_dependencies(store: GraphStore, entity_id: str) -> DirectDependencies | None:
    """FR3: direct (exactly one-hop) upstream and downstream dependencies of
    an entity -- upstream is what it depends on (outbound dependency
    edges), downstream is what depends on it (inbound dependency edges),
    per the glossary in `PRODUCT_BRIEF.md`. Returns `None` if `entity_id`
    doesn't match any node.
    """
    nodes = store.get_all_nodes()
    node_by_id = {n["id"]: n for n in nodes}
    if entity_id not in node_by_id:
        return None

    upstream: list[DependencyEdge] = []
    downstream: list[DependencyEdge] = []
    for rel in _dependency_relationships(store):
        if rel["source_id"] == entity_id and rel["target_id"] in node_by_id:
            other = node_by_id[rel["target_id"]]
            upstream.append(DependencyEdge(entity=_entity_ref(other), rel_type=rel["rel_type"]))
        if rel["target_id"] == entity_id and rel["source_id"] in node_by_id:
            other = node_by_id[rel["source_id"]]
            downstream.append(DependencyEdge(entity=_entity_ref(other), rel_type=rel["rel_type"]))

    upstream.sort(key=lambda edge: (edge.rel_type, edge.entity.name))
    downstream.sort(key=lambda edge: (edge.rel_type, edge.entity.name))
    return DirectDependencies(upstream=upstream, downstream=downstream)


# FR4 is explicitly a *bounded* traversal (see PROJECT_CHARTER.md's
# constraints) -- a UI-facing depth control that could crawl the whole
# graph would defeat the point of "configurable depth" as a scoping tool.
DEFAULT_TRAVERSAL_DEPTH = 2
MAX_TRAVERSAL_DEPTH = 5


@dataclass(frozen=True)
class TraversalNode:
    entity: EntityRef
    depth: int  # 0 = the root entity itself


@dataclass(frozen=True)
class TraversalEdge:
    source_id: str
    target_id: str
    rel_type: str


@dataclass(frozen=True)
class TraversalResult:
    root_id: str
    direction: TraversalDirection
    max_depth: int
    nodes: list[TraversalNode]
    edges: list[TraversalEdge]


def get_dependency_traversal(
    store: GraphStore,
    entity_id: str,
    direction: TraversalDirection,
    max_depth: int = DEFAULT_TRAVERSAL_DEPTH,
) -> TraversalResult | None:
    """FR4/FR5: BFS out from `entity_id` through dependency edges only
    (same `DEPENDENCY_REL_TYPES` restriction as FR3), up to `max_depth`
    hops in the given direction, returning every reached node (with its
    depth) plus *every* dependency edge between two reached nodes -- not
    just the BFS tree edges -- so a rendered subgraph (FR5) shows real
    cross-links between sibling nodes, not an artificially tree-shaped view.
    Returns `None` if `entity_id` doesn't match any node.
    """
    if direction not in ("upstream", "downstream"):
        raise ValueError(f"direction must be 'upstream' or 'downstream', got {direction!r}")

    nodes = store.get_all_nodes()
    node_by_id = {n["id"]: n for n in nodes}
    if entity_id not in node_by_id:
        return None
    max_depth = max(1, min(max_depth, MAX_TRAVERSAL_DEPTH))

    dependency_rels = _dependency_relationships(store)
    adjacency: dict[str, list[str]] = {}
    for rel in dependency_rels:
        step_from, step_to = (
            (rel["source_id"], rel["target_id"])
            if direction == "upstream"
            else (rel["target_id"], rel["source_id"])
        )
        adjacency.setdefault(step_from, []).append(step_to)

    depth_by_id: dict[str, int] = {entity_id: 0}
    frontier = [entity_id]
    for depth in range(1, max_depth + 1):
        next_frontier = []
        for current_id in frontier:
            for neighbor_id in adjacency.get(current_id, []):
                if neighbor_id in depth_by_id or neighbor_id not in node_by_id:
                    continue
                depth_by_id[neighbor_id] = depth
                next_frontier.append(neighbor_id)
        frontier = next_frontier
        if not frontier:
            break

    traversal_nodes = [
        TraversalNode(entity=_entity_ref(node_by_id[node_id]), depth=node_depth)
        for node_id, node_depth in sorted(
            depth_by_id.items(), key=lambda item: (item[1], node_by_id[item[0]]["name"])
        )
    ]
    traversal_edges = [
        TraversalEdge(
            source_id=rel["source_id"], target_id=rel["target_id"], rel_type=rel["rel_type"]
        )
        for rel in dependency_rels
        if rel["source_id"] in depth_by_id and rel["target_id"] in depth_by_id
    ]
    return TraversalResult(
        root_id=entity_id,
        direction=direction,
        max_depth=max_depth,
        nodes=traversal_nodes,
        edges=traversal_edges,
    )


# FR6/FR7 "dependency path investigation" (golden question 5) treats
# dependency edges as undirected for connectivity: what an investigator
# needs is *whether* two systems are linked and how, not which one is
# formally upstream of the other for any single hop along the way. A
# path can legitimately step "downstream" for one hop and "upstream" for
# the next -- that's real topology, not a bug -- so each `PathEdge` keeps
# the original relationship's direction rather than implying a consistent
# one across the whole walk.
ALTERNATE_PATH_SLACK = 2
MAX_ALTERNATE_PATHS = 3
# Hard ceiling on any path considered at all, independent of how long the
# shortest path turns out to be -- protects the DFS enumeration below from
# a pathologically dense future graph.
MAX_PATH_HOPS = 8


@dataclass(frozen=True)
class PathEdge:
    source_id: str
    target_id: str
    rel_type: str


@dataclass(frozen=True)
class DependencyPath:
    """One source-to-target walk: `nodes[0]` is the source, `nodes[-1]` is
    the target, and `edges[i]` connects `nodes[i]` to `nodes[i + 1]`.
    """

    nodes: list[EntityRef]
    edges: list[PathEdge]

    @property
    def hops(self) -> int:
        return len(self.edges)


@dataclass(frozen=True)
class PathSearchResult:
    source_id: str
    target_id: str
    shortest: DependencyPath | None  # None only when no path connects them
    alternates: list[DependencyPath]


def _bfs_shortest_path_ids(
    adjacency: dict[str, list[tuple[str, dict]]], source_id: str, target_id: str
) -> list[str] | None:
    parent: dict[str, str] = {}
    visited = {source_id}
    frontier = [source_id]
    while frontier and target_id not in visited:
        next_frontier = []
        for current_id in frontier:
            for neighbor_id, _rel in adjacency.get(current_id, []):
                if neighbor_id in visited:
                    continue
                visited.add(neighbor_id)
                parent[neighbor_id] = current_id
                next_frontier.append(neighbor_id)
        frontier = next_frontier

    if target_id not in visited:
        return None

    path_ids = [target_id]
    while path_ids[-1] != source_id:
        path_ids.append(parent[path_ids[-1]])
    path_ids.reverse()
    return path_ids


def _enumerate_simple_paths(
    adjacency: dict[str, list[tuple[str, dict]]],
    source_id: str,
    target_id: str,
    max_hops: int,
    max_paths_explored: int = 200,
) -> list[tuple[list[str], list[dict]]]:
    """DFS enumeration of every simple (no repeated node) walk from
    `source_id` to `target_id` of at most `max_hops` edges, capped at
    `max_paths_explored` complete paths so a denser future graph can't
    make FR7 hang.
    """
    found: list[tuple[list[str], list[dict]]] = []
    path_ids = [source_id]
    edge_trail: list[dict] = []
    visited = {source_id}

    def dfs(current_id: str) -> None:
        if len(found) >= max_paths_explored:
            return
        if current_id == target_id:
            found.append((list(path_ids), list(edge_trail)))
            return
        if len(path_ids) - 1 >= max_hops:
            return
        for neighbor_id, rel in adjacency.get(current_id, []):
            if neighbor_id in visited or len(found) >= max_paths_explored:
                continue
            visited.add(neighbor_id)
            path_ids.append(neighbor_id)
            edge_trail.append(rel)
            dfs(neighbor_id)
            edge_trail.pop()
            path_ids.pop()
            visited.remove(neighbor_id)

    dfs(source_id)
    return found


def _to_dependency_path(
    node_by_id: dict[str, dict], path_ids: list[str], rels: list[dict]
) -> DependencyPath:
    return DependencyPath(
        nodes=[_entity_ref(node_by_id[node_id]) for node_id in path_ids],
        edges=[
            PathEdge(
                source_id=rel["source_id"],
                target_id=rel["target_id"],
                rel_type=rel["rel_type"],
            )
            for rel in rels
        ],
    )


def get_dependency_paths(
    store: GraphStore, source_id: str, target_id: str
) -> PathSearchResult | None:
    """FR6/FR7: the shortest dependency path between two entities, plus up
    to `MAX_ALTERNATE_PATHS` distinct alternates no more than
    `ALTERNATE_PATH_SLACK` hops longer. Returns `None` if either id doesn't
    match a node; returns a result with `shortest=None` if both exist but
    no dependency path connects them.
    """
    nodes = store.get_all_nodes()
    node_by_id = {n["id"]: n for n in nodes}
    if source_id not in node_by_id or target_id not in node_by_id:
        return None

    if source_id == target_id:
        trivial = DependencyPath(nodes=[_entity_ref(node_by_id[source_id])], edges=[])
        return PathSearchResult(
            source_id=source_id, target_id=target_id, shortest=trivial, alternates=[]
        )

    adjacency: dict[str, list[tuple[str, dict]]] = {}
    for rel in _dependency_relationships(store):
        adjacency.setdefault(rel["source_id"], []).append((rel["target_id"], rel))
        adjacency.setdefault(rel["target_id"], []).append((rel["source_id"], rel))

    shortest_ids = _bfs_shortest_path_ids(adjacency, source_id, target_id)
    if shortest_ids is None:
        return PathSearchResult(
            source_id=source_id, target_id=target_id, shortest=None, alternates=[]
        )

    max_hops = min(len(shortest_ids) - 1 + ALTERNATE_PATH_SLACK, MAX_PATH_HOPS)
    raw_paths = _enumerate_simple_paths(adjacency, source_id, target_id, max_hops=max_hops)

    seen_sequences: set[tuple[str, ...]] = set()
    candidates: list[tuple[list[str], list[dict]]] = []
    for path_ids, rels in raw_paths:
        key = tuple(path_ids)
        if key in seen_sequences:
            continue
        seen_sequences.add(key)
        candidates.append((path_ids, rels))
    candidates.sort(key=lambda item: (len(item[0]), [node_by_id[i]["name"] for i in item[0]]))

    dependency_paths = [_to_dependency_path(node_by_id, ids, rels) for ids, rels in candidates]
    return PathSearchResult(
        source_id=source_id,
        target_id=target_id,
        shortest=dependency_paths[0],
        alternates=dependency_paths[1 : 1 + MAX_ALTERNATE_PATHS],
    )


def _owner_by_entity_id(store: GraphStore) -> dict[str, str]:
    return {
        rel["source_id"]: rel["target_id"]
        for rel in store.get_all_relationships()
        if rel["rel_type"] == "OWNED_BY"
    }


def get_owning_team(store: GraphStore, entity_id: str) -> OwnerRef | None:
    """FR8: the team that owns a single entity, if any. `get_entity_detail`
    (FR2) already surfaces this for its one entity; this is the standalone
    primitive for callers -- namely the NL query layer (increment-13) --
    that only need the owner and not the rest of the entity's detail.
    Returns `None` for an unknown entity id or an unowned entity alike
    (this is a lookup, not an existence check -- callers that need to
    distinguish those should check `get_entity_detail` first).
    """
    nodes = store.get_all_nodes()
    node_by_id = {n["id"]: n for n in nodes}
    owner_id = _owner_by_entity_id(store).get(entity_id)
    if owner_id is None or owner_id not in node_by_id:
        return None
    owner_node = node_by_id[owner_id]
    return OwnerRef(id=owner_node["id"], name=owner_node["name"])


@dataclass(frozen=True)
class OwnershipGroup:
    """Every entity in the traversed subtree owned by one team --
    `team=None` is the "no owning team recorded" bucket, kept rather than
    dropped so a stakeholder rollup can flag ownership gaps.
    """

    team: OwnerRef | None
    entities: list[EntityRef]


@dataclass(frozen=True)
class OwnershipRollup:
    root_id: str
    direction: TraversalDirection
    max_depth: int
    groups: list[OwnershipGroup]


def get_ownership_rollup(
    store: GraphStore,
    entity_id: str,
    direction: TraversalDirection,
    max_depth: int = DEFAULT_TRAVERSAL_DEPTH,
) -> OwnershipRollup | None:
    """FR9: every distinct owning team across `entity_id`'s dependency
    subtree (the same bounded `get_dependency_traversal` used by FR4/FR5)
    -- "which teams do I need in the room before I change this system"
    (`PRODUCT_BRIEF.md`'s TPM persona). Includes the root entity itself
    (depth 0): its own team obviously belongs in that conversation.
    Returns `None` if `entity_id` doesn't match a node.
    """
    traversal = get_dependency_traversal(store, entity_id, direction, max_depth=max_depth)
    if traversal is None:
        return None

    owner_by_entity_id = _owner_by_entity_id(store)
    node_by_id = {n["id"]: n for n in store.get_all_nodes()}

    entities_by_owner_id: dict[str | None, list[EntityRef]] = {}
    for traversal_node in traversal.nodes:
        owner_id = owner_by_entity_id.get(traversal_node.entity.id)
        if owner_id is not None and owner_id not in node_by_id:
            owner_id = None
        entities_by_owner_id.setdefault(owner_id, []).append(traversal_node.entity)

    groups = [
        OwnershipGroup(
            team=OwnerRef(id=node_by_id[owner_id]["id"], name=node_by_id[owner_id]["name"])
            if owner_id is not None
            else None,
            entities=sorted(entities, key=lambda e: e.name),
        )
        for owner_id, entities in entities_by_owner_id.items()
    ]
    groups.sort(key=lambda g: (g.team is None, g.team.name if g.team else ""))

    return OwnershipRollup(
        root_id=entity_id,
        direction=direction,
        max_depth=traversal.max_depth,
        groups=groups,
    )
