"""Read-only retirement what-if simulation (`ADR-0008`, FR24)."""

from __future__ import annotations

from dataclasses import dataclass, field

from src.graph.queries import (
    DEFAULT_TRAVERSAL_DEPTH,
    EntityRef,
    OwnerRef,
    get_capability_rollup,
    get_dependency_traversal,
    get_direct_dependencies,
    get_entity_detail,
    get_ownership_rollup,
)
from src.graph.store import GraphStore
from src.intelligence.risk import RiskAssessment, compute_risk_score


@dataclass(frozen=True)
class WhatIfResult:
    seed: EntityRef
    scenario: str
    max_depth: int
    downstream: list[EntityRef]
    upstream_critical: list[EntityRef]
    stakeholder_teams: list[OwnerRef]
    unowned_entities: list[EntityRef]
    capabilities: list[EntityRef]
    top_impacted: list[RiskAssessment] = field(default_factory=list)
    narrative: str | None = None


def simulate_retirement(
    store: GraphStore,
    entity_id: str,
    *,
    max_depth: int = DEFAULT_TRAVERSAL_DEPTH,
    top_n: int = 8,
) -> WhatIfResult | None:
    """Simulate retiring `entity_id` without writing to the graph."""
    detail = get_entity_detail(store, entity_id)
    if detail is None:
        return None

    seed = EntityRef(
        id=detail.id,
        label=detail.label,
        name=detail.name,
        criticality=detail.criticality,
        lifecycle_status=detail.lifecycle_status,
    )

    down = get_dependency_traversal(
        store, entity_id, "downstream", max_depth=max_depth
    )
    downstream = [
        n.entity for n in (down.nodes if down else []) if n.entity.id != entity_id
    ]

    deps = get_direct_dependencies(store, entity_id)
    upstream_critical: list[EntityRef] = []
    if deps:
        for edge in deps.upstream:
            crit = (edge.entity.criticality or "").lower()
            if crit in {"critical", "high"}:
                upstream_critical.append(edge.entity)

    rollup = get_ownership_rollup(
        store, entity_id, "downstream", max_depth=max_depth
    )
    teams: list[OwnerRef] = []
    unowned: list[EntityRef] = []
    if rollup:
        for group in rollup.groups:
            if group.team is None:
                unowned.extend(group.entities)
            else:
                teams.append(group.team)

    caps = get_capability_rollup(
        store, entity_id, "downstream", max_depth=max_depth
    )
    capabilities = [g.capability for g in (caps.groups if caps else [])]

    scored: list[RiskAssessment] = []
    for entity in downstream[:40]:
        assessment = compute_risk_score(store, entity.id, max_depth=max_depth)
        if assessment is not None:
            scored.append(assessment)
    scored.sort(key=lambda a: (-a.score, a.entity_name))

    return WhatIfResult(
        seed=seed,
        scenario="retire",
        max_depth=max_depth,
        downstream=downstream,
        upstream_critical=upstream_critical,
        stakeholder_teams=teams,
        unowned_entities=unowned,
        capabilities=capabilities,
        top_impacted=scored[:top_n],
    )
