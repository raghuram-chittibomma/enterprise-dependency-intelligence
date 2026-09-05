"""Unit tests for MVP5 deterministic intelligence (`ADR-0008`)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.graph.fallback_store import FallbackGraphStore
from src.intelligence.drift import detect_drift
from src.intelligence.narrative import narrate_risk
from src.intelligence.rationalization import rationalize_technologies
from src.intelligence.risk import compute_risk_score
from src.intelligence.whatif import simulate_retirement
from src.ontology.entities import API, Application, Database, Team
from src.ontology.relationships import Consumes, OwnedBy, ReplacedBy
from src.ontology.types import Criticality, LifecycleStatus


@pytest.fixture
def store(tmp_path: Path):
    graph = FallbackGraphStore(sqlite_path=":memory:")
    graph.upsert_node(
        "API",
        API(
            id="api:1",
            name="Legacy Customer API",
            source_system="api-catalog",
            source_record_id="1",
            version="v1",
            protocol="REST",
            criticality=Criticality.CRITICAL,
            lifecycle_status=LifecycleStatus.DEPRECATED,
        ),
    )
    graph.upsert_node(
        "API",
        API(
            id="api:2",
            name="Customer API v2",
            source_system="api-catalog",
            source_record_id="2",
            version="v2",
            protocol="REST",
            criticality=Criticality.HIGH,
            lifecycle_status=LifecycleStatus.ACTIVE,
        ),
    )
    graph.upsert_node(
        "Application",
        Application(
            id="app:1",
            name="Storefront",
            source_system="cmdb",
            source_record_id="1",
            technology="React",
            environment="prod",
            criticality=Criticality.CRITICAL,
        ),
    )
    graph.upsert_node(
        "Application",
        Application(
            id="app:2",
            name="Order Service UI",
            source_system="cmdb",
            source_record_id="2",
            technology="Java",
            environment="prod",
            criticality=Criticality.HIGH,
        ),
    )
    graph.upsert_node(
        "Database",
        Database(
            id="db:1",
            name="Customer DB",
            source_system="db-metadata",
            source_record_id="1",
            engine="PostgreSQL",
            criticality=Criticality.HIGH,
        ),
    )
    graph.upsert_node(
        "Team",
        Team(
            id="team:1",
            name="Commerce Team",
            source_system="team-ownership",
            source_record_id="1",
            business_area="Commerce",
        ),
    )
    graph.upsert_relationship(
        "OWNED_BY",
        OwnedBy(
            source_id="app:1",
            target_id="team:1",
            source_system="team-ownership",
            source_record_id="1",
        ),
        "Application",
        "Team",
    )
    graph.upsert_relationship(
        "CONSUMES",
        Consumes(
            source_id="app:1",
            target_id="api:1",
            source_system="api-catalog",
            source_record_id="c1",
        ),
        "Application",
        "API",
    )
    graph.upsert_relationship(
        "CONSUMES",
        Consumes(
            source_id="app:2",
            target_id="api:1",
            source_system="api-catalog",
            source_record_id="c2",
        ),
        "Application",
        "API",
    )
    graph.upsert_relationship(
        "REPLACED_BY",
        ReplacedBy(
            source_id="api:1",
            target_id="api:2",
            source_system="cmdb",
            source_record_id="r1",
        ),
        "API",
        "API",
    )
    unresolved = tmp_path / "unresolved.json"
    unresolved.write_text(
        json.dumps(
            [
                {
                    "name": "Ghost Service",
                    "entity_type": "Service",
                    "referenced_by_source": "integration-catalog",
                    "referenced_by_record_id": "x1",
                }
            ]
        ),
        encoding="utf-8",
    )
    yield graph, unresolved
    graph.close()


def test_risk_score_bands_and_factors(store) -> None:
    graph, _ = store
    assessment = compute_risk_score(graph, "api:1")
    assert assessment is not None
    assert assessment.score == min(100, sum(f.points for f in assessment.factors))
    assert 0 <= assessment.score <= 100
    assert assessment.band in {"low", "medium", "high", "critical"}
    ids = {f.id for f in assessment.factors}
    assert ids == {
        "criticality",
        "lifecycle",
        "blast_radius",
        "fan_in",
        "ownership_gap",
        "capability_exposure",
    }
    # Deprecated + critical + consumers should be elevated.
    assert assessment.score >= 50


def test_whatif_retire_non_mutating(store) -> None:
    graph, _ = store
    before = len(graph.get_all_relationships())
    result = simulate_retirement(graph, "api:1")
    assert result is not None
    assert result.scenario == "retire"
    assert {e.id for e in result.downstream} >= {"app:1", "app:2"}
    assert len(graph.get_all_relationships()) == before


def test_drift_lifecycle_replacement_resolution(store) -> None:
    graph, unresolved = store
    signals = detect_drift(graph, unresolved_path=unresolved)
    kinds = {s.kind for s in signals}
    assert "lifecycle" in kinds
    assert "replacement" in kinds
    assert "resolution" in kinds
    assert any(s.entity_id == "api:1" for s in signals if s.kind == "lifecycle")


def test_rationalization_groups_tech_and_engine(store) -> None:
    graph, _ = store
    report = rationalize_technologies(graph)
    tech_keys = {b.key for b in report.technology_buckets}
    engine_keys = {b.key for b in report.engine_buckets}
    assert "React" in tech_keys
    assert "Java" in tech_keys
    assert "PostgreSQL" in engine_keys


def test_narrative_rejects_unknown_factor_ids(store) -> None:
    graph, _ = store
    assessment = compute_risk_score(graph, "api:1")
    assert assessment is not None

    class BadClient:
        def complete(self, *, system: str, user: str) -> str:
            return json.dumps(
                {
                    "status": "ok",
                    "text": "Invented",
                    "cited_factor_ids": ["not_a_real_factor"],
                }
            )

    out = narrate_risk(assessment, client=BadClient())
    assert out.narrative is None
    assert out.score == assessment.score


def test_narrative_accepts_valid_citations(store) -> None:
    graph, _ = store
    assessment = compute_risk_score(graph, "api:1")
    assert assessment is not None

    class GoodClient:
        def complete(self, *, system: str, user: str) -> str:
            return json.dumps(
                {
                    "status": "ok",
                    "text": "High fan-in and deprecated lifecycle drive risk.",
                    "cited_factor_ids": ["fan_in", "lifecycle"],
                }
            )

    out = narrate_risk(assessment, client=GoodClient())
    assert out.narrative is not None
    assert "fan-in" in out.narrative.lower() or "deprecated" in out.narrative.lower()


def test_team_ownership_gap_not_penalized(store) -> None:
    graph, _ = store
    assessment = compute_risk_score(graph, "team:1")
    assert assessment is not None
    gap = next(f for f in assessment.factors if f.id == "ownership_gap")
    assert gap.points == 0
    assert "N/A" in gap.label
    assert assessment.score == sum(f.points for f in assessment.factors)


def test_team_owned_systems_risk_rollup(store) -> None:
    from src.intelligence.team_rollup import compute_team_owned_risk_rollup

    graph, _ = store
    rollup = compute_team_owned_risk_rollup(graph, "team:1")
    assert rollup is not None
    assert rollup.owned_count >= 1
    assert any(a.entity_id == "app:1" for a in rollup.systems)
    assert rollup.max_score == max(a.score for a in rollup.systems)


def test_team_portfolio_whatif_unions_blast(store) -> None:
    from src.intelligence.team_rollup import simulate_team_portfolio_impact

    graph, _ = store
    portfolio = simulate_team_portfolio_impact(graph, "team:1")
    assert portfolio is not None
    assert any(e.id == "app:1" for e in portfolio.owned_systems)
