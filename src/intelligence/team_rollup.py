"""Team owned-systems risk rollup (`ADR-0008`).

Teams are not scored as dependency-graph nodes. Instead we roll up FR23
risk (and a portfolio-style what-if) over systems they own via OWNED_BY.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from src.graph.queries import (
    DEFAULT_TRAVERSAL_DEPTH,
    EntityRef,
    OwnerRef,
    get_entities_owned_by_team,
    get_entity_detail,
)
from src.graph.store import GraphStore
from src.intelligence.models import RiskAssessment, RiskBand
from src.intelligence.risk import compute_risk_score
from src.intelligence.whatif import WhatIfResult, simulate_retirement


def _band(score: int) -> RiskBand:
    if score >= 75:
        return "critical"
    if score >= 50:
        return "high"
    if score >= 25:
        return "medium"
    return "low"


@dataclass(frozen=True)
class TeamOwnedRiskRollup:
    team_id: str
    team_name: str
    owned_count: int
    max_score: int
    avg_score: int
    band: RiskBand
    band_mix: dict[str, int]
    systems: list[RiskAssessment] = field(default_factory=list)


@dataclass(frozen=True)
class TeamPortfolioWhatIf:
    team_id: str
    team_name: str
    max_depth: int
    owned_systems: list[EntityRef]
    union_downstream: list[EntityRef]
    stakeholder_teams: list[OwnerRef]
    capabilities: list[EntityRef]
    system_whatifs: list[WhatIfResult] = field(default_factory=list)
    top_owned_by_risk: list[RiskAssessment] = field(default_factory=list)


def compute_team_owned_risk_rollup(
    store: GraphStore,
    team_id: str,
    *,
    max_depth: int = DEFAULT_TRAVERSAL_DEPTH,
) -> TeamOwnedRiskRollup | None:
    detail = get_entity_detail(store, team_id)
    if detail is None or detail.label != "Team":
        return None
    owned = get_entities_owned_by_team(store, team_id)
    if owned is None:
        return None

    systems: list[RiskAssessment] = []
    for entity in owned:
        assessment = compute_risk_score(store, entity.id, max_depth=max_depth)
        if assessment is not None:
            systems.append(assessment)
    systems.sort(key=lambda a: (-a.score, a.entity_name))

    if not systems:
        return TeamOwnedRiskRollup(
            team_id=detail.id,
            team_name=detail.name,
            owned_count=0,
            max_score=0,
            avg_score=0,
            band="low",
            band_mix={},
            systems=[],
        )

    scores = [a.score for a in systems]
    max_score = max(scores)
    avg_score = int(round(sum(scores) / len(scores)))
    band_mix: dict[str, int] = {}
    for a in systems:
        band_mix[a.band] = band_mix.get(a.band, 0) + 1

    return TeamOwnedRiskRollup(
        team_id=detail.id,
        team_name=detail.name,
        owned_count=len(systems),
        max_score=max_score,
        avg_score=avg_score,
        band=_band(max_score),
        band_mix=dict(sorted(band_mix.items())),
        systems=systems,
    )


def simulate_team_portfolio_impact(
    store: GraphStore,
    team_id: str,
    *,
    max_depth: int = DEFAULT_TRAVERSAL_DEPTH,
    top_n: int = 8,
) -> TeamPortfolioWhatIf | None:
    """Union of retirement blast radii across systems owned by the team."""
    detail = get_entity_detail(store, team_id)
    if detail is None or detail.label != "Team":
        return None
    owned = get_entities_owned_by_team(store, team_id)
    if owned is None:
        return None

    system_whatifs: list[WhatIfResult] = []
    down_by_id: dict[str, EntityRef] = {}
    teams_by_id: dict[str, OwnerRef] = {}
    caps_by_id: dict[str, EntityRef] = {}

    for entity in owned:
        result = simulate_retirement(store, entity.id, max_depth=max_depth, top_n=top_n)
        if result is None:
            continue
        system_whatifs.append(result)
        for e in result.downstream:
            down_by_id[e.id] = e
        for t in result.stakeholder_teams:
            teams_by_id[t.id] = t
        for c in result.capabilities:
            caps_by_id[c.id] = c

    rollup = compute_team_owned_risk_rollup(store, team_id, max_depth=max_depth)
    top_owned = list(rollup.systems[:top_n]) if rollup else []

    return TeamPortfolioWhatIf(
        team_id=detail.id,
        team_name=detail.name,
        max_depth=max_depth,
        owned_systems=owned,
        union_downstream=sorted(down_by_id.values(), key=lambda e: e.name),
        stakeholder_teams=sorted(teams_by_id.values(), key=lambda t: t.name),
        capabilities=sorted(caps_by_id.values(), key=lambda c: c.name),
        system_whatifs=system_whatifs,
        top_owned_by_risk=top_owned,
    )
