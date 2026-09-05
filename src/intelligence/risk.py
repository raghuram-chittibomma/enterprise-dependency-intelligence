"""Deterministic change-risk scoring (`ADR-0008`, FR23)."""

from __future__ import annotations

from src.graph.queries import (
    DEFAULT_TRAVERSAL_DEPTH,
    get_capability_rollup,
    get_dependency_traversal,
    get_direct_dependencies,
    get_entity_detail,
    get_ownership_rollup,
    get_owning_team,
)
from src.graph.store import GraphStore
from src.intelligence.models import EvidenceRef, RiskAssessment, RiskBand, RiskFactor

CRITICALITY_POINTS = {
    "critical": 25,
    "high": 18,
    "medium": 10,
    "low": 4,
}

LIFECYCLE_POINTS = {
    "deprecated": 15,
    "retired": 12,
    "planned": 5,
}


def _band(score: int) -> RiskBand:
    if score >= 75:
        return "critical"
    if score >= 50:
        return "high"
    if score >= 25:
        return "medium"
    return "low"


def compute_risk_score(
    store: GraphStore,
    entity_id: str,
    *,
    max_depth: int = DEFAULT_TRAVERSAL_DEPTH,
) -> RiskAssessment | None:
    """Return a 0–100 risk assessment for `entity_id`, or None if missing."""
    detail = get_entity_detail(store, entity_id)
    if detail is None:
        return None

    factors: list[RiskFactor] = []

    crit = (detail.criticality or "").lower()
    crit_pts = CRITICALITY_POINTS.get(crit, 0)
    factors.append(
        RiskFactor(
            id="criticality",
            label=f"Criticality ({detail.criticality or 'unset'})",
            points=crit_pts,
            evidence=[
                EvidenceRef(
                    kind="property",
                    label="criticality",
                    entity_id=entity_id,
                    detail=detail.criticality or "unset",
                )
            ],
        )
    )

    life = (detail.lifecycle_status or "active").lower()
    life_pts = LIFECYCLE_POINTS.get(life, 0)
    factors.append(
        RiskFactor(
            id="lifecycle",
            label=f"Lifecycle ({detail.lifecycle_status})",
            points=life_pts,
            evidence=[
                EvidenceRef(
                    kind="property",
                    label="lifecycle_status",
                    entity_id=entity_id,
                    detail=detail.lifecycle_status,
                )
            ],
        )
    )

    traversal = get_dependency_traversal(
        store, entity_id, "downstream", max_depth=max_depth
    )
    blast_nodes = len(traversal.nodes) if traversal else 1
    blast_others = max(0, blast_nodes - 1)
    blast_pts = min(20, blast_others * 2)
    factors.append(
        RiskFactor(
            id="blast_radius",
            label=f"Downstream blast radius ({blast_others} entities within depth {max_depth})",
            points=blast_pts,
            evidence=[
                EvidenceRef(
                    kind="entity",
                    label=n.entity.name,
                    entity_id=n.entity.id,
                    detail=f"depth={n.depth}",
                )
                for n in (traversal.nodes if traversal else [])
                if n.entity.id != entity_id
            ][:12],
        )
    )

    deps = get_direct_dependencies(store, entity_id)
    fan_in = len(deps.downstream) if deps else 0
    fan_pts = min(15, fan_in * 3)
    factors.append(
        RiskFactor(
            id="fan_in",
            label=f"Direct consumers ({fan_in})",
            points=fan_pts,
            evidence=[
                EvidenceRef(
                    kind="edge",
                    label=f"{edge.rel_type} ← {edge.entity.name}",
                    entity_id=edge.entity.id,
                    detail=edge.rel_type,
                )
                for edge in (deps.downstream if deps else [])
            ][:12],
        )
    )

    owner = get_owning_team(store, entity_id)
    # Teams (and similar non-owned types) are ownership roots — missing OWNED_BY
    # is expected, not a change-risk signal.
    if detail.label in {"Team", "BusinessCapability", "Document"}:
        own_pts = 0
        own_label = f"Ownership gap N/A for {detail.label}"
        owner_detail = "n/a"
    else:
        rollup = get_ownership_rollup(
            store, entity_id, "downstream", max_depth=max_depth
        )
        total_entities = 0
        unowned = 0
        if rollup:
            for group in rollup.groups:
                total_entities += len(group.entities)
                if group.team is None:
                    unowned += len(group.entities)
        if owner is None:
            own_pts = 10
            own_label = "Seed entity has no owning team"
            owner_detail = "missing"
        elif total_entities > 0:
            unowned_pct = unowned / total_entities
            own_pts = min(15, int(unowned_pct * 15))
            own_label = (
                f"Ownership gaps in subtree ({unowned}/{total_entities} without owner)"
            )
            owner_detail = owner.name
        else:
            own_pts = 0
            own_label = "Ownership recorded"
            owner_detail = owner.name
    factors.append(
        RiskFactor(
            id="ownership_gap",
            label=own_label,
            points=own_pts,
            evidence=[
                EvidenceRef(
                    kind="property",
                    label="owner",
                    entity_id=entity_id,
                    detail=owner_detail,
                )
            ],
        )
    )

    caps = get_capability_rollup(
        store, entity_id, "downstream", max_depth=max_depth
    )
    cap_count = len(caps.groups) if caps else 0
    cap_pts = min(15, cap_count * 3)
    factors.append(
        RiskFactor(
            id="capability_exposure",
            label=f"Capability exposure ({cap_count} capabilities in rollup)",
            points=cap_pts,
            evidence=[
                EvidenceRef(
                    kind="entity",
                    label=g.capability.name,
                    entity_id=g.capability.id,
                )
                for g in (caps.groups if caps else [])
            ][:12],
        )
    )

    score = min(100, sum(f.points for f in factors))
    return RiskAssessment(
        entity_id=detail.id,
        entity_name=detail.name,
        entity_label=detail.label,
        score=score,
        band=_band(score),
        factors=factors,
    )
