"""Golden-dataset runner (increment-15). Every scenario in
`evals/scenarios.py` must pass 100% -- see EVAL_STRATEGY.md.
"""

from __future__ import annotations

import pytest

from evals.scenarios import SCENARIOS
from src.graph.queries import (
    get_capability_rollup,
    get_dependency_paths,
    get_dependency_traversal,
    get_direct_dependencies,
    get_entity_detail,
    get_entity_evidence,
    get_ownership_rollup,
    get_owning_team,
    search_entities,
)
from src.nlquery.ask import ask


def _nl_scenarios() -> list[dict]:
    return [s for s in SCENARIOS if "question" in s]


def _structured_scenarios() -> list[dict]:
    return [s for s in SCENARIOS if "kind" in s]


@pytest.mark.parametrize("scenario", _nl_scenarios(), ids=lambda s: s["id"])
def test_nl_golden_scenario(store, scenario: dict) -> None:
    answer = ask(store, scenario["question"])
    assert answer.status == scenario["expected_status"], answer.text

    if scenario.get("expected_question_type") is not None:
        assert answer.question_type == scenario["expected_question_type"]

    resolved_ids = [entity.id for entity in answer.resolved_entities]
    assert resolved_ids == scenario.get("expected_entities", [])

    for name in scenario.get("expected_entity_names", []):
        assert name in answer.text, f"expected {name!r} in answer text: {answer.text}"

    evidence_types = {edge.rel_type for edge in answer.evidence}
    for rel_type in scenario.get("expected_relationship_types", []):
        assert rel_type in evidence_types, (
            f"expected relationship type {rel_type!r} in evidence {evidence_types}"
        )

    if "expected_path" in scenario:
        # Path answer text encodes the shortest chain as "A -[REL]-> B -[REL]-> C".
        for name in scenario["expected_path"]:
            assert name in answer.text


@pytest.mark.parametrize("scenario", _structured_scenarios(), ids=lambda s: s["id"])
def test_structured_golden_scenario(store, scenario: dict) -> None:
    kind = scenario["kind"]

    if kind == "search":
        results = search_entities(store, scenario["query"])
        assert results
        assert results[0].id == scenario["expected_top_id"]
        assert results[0].name == scenario["expected_top_name"]
        return

    if kind == "detail":
        detail = get_entity_detail(store, scenario["entity_id"])
        assert detail is not None
        assert detail.name == scenario["expected_name"]
        assert detail.owner is not None
        assert detail.owner.name == scenario["expected_owner_name"]
        assert detail.source_system == scenario["expected_source_system"]
        return

    if kind == "direct_deps":
        deps = get_direct_dependencies(store, scenario["entity_id"])
        assert deps is not None
        upstream_names = {edge.entity.name for edge in deps.upstream}
        assert set(scenario["expected_upstream_names"]) <= upstream_names
        upstream_rels = {edge.rel_type for edge in deps.upstream}
        assert set(scenario["expected_upstream_rel_types"]) <= upstream_rels
        downstream_names = {edge.entity.name for edge in deps.downstream}
        assert set(scenario["expected_downstream_names"]) <= downstream_names
        return

    if kind == "traversal":
        result = get_dependency_traversal(
            store,
            scenario["entity_id"],
            scenario["direction"],
            max_depth=scenario["max_depth"],
        )
        assert result is not None
        names = {node.entity.name for node in result.nodes}
        assert set(scenario["expected_node_names"]) <= names
        return

    if kind == "path":
        result = get_dependency_paths(store, scenario["source_id"], scenario["target_id"])
        assert result is not None and result.shortest is not None
        assert [node.name for node in result.shortest.nodes] == scenario["expected_path"]
        assert [edge.rel_type for edge in result.shortest.edges] == scenario["expected_rel_types"]
        assert len(result.alternates) >= scenario["expected_min_alternates"]
        return

    if kind == "owning_team":
        owner = get_owning_team(store, scenario["entity_id"])
        assert owner is not None
        assert owner.name == scenario["expected_owner_name"]
        return

    if kind == "ownership_rollup":
        rollup = get_ownership_rollup(store, scenario["entity_id"], scenario["direction"])
        assert rollup is not None
        team_names = {group.team.name for group in rollup.groups if group.team is not None}
        assert set(scenario["expected_team_names"]) <= team_names
        return

    if kind == "capability_rollup":
        rollup = get_capability_rollup(store, scenario["entity_id"], scenario["direction"])
        assert rollup is not None
        names = {group.capability.name for group in rollup.groups}
        assert set(scenario["expected_capability_names"]) <= names
        return

    if kind == "evidence":
        evidence = get_entity_evidence(store, scenario["entity_id"])
        assert evidence is not None
        assert len(evidence.items) >= scenario["expected_min_items"]
        rel_types = {item.rel_type for item in evidence.items}
        assert set(scenario["expected_rel_types"]) <= rel_types
        assert all(
            item.evidence_type == scenario["expected_evidence_type"] for item in evidence.items
        )
        source_systems = {item.source_system for item in evidence.items}
        assert set(scenario["expected_source_systems"]) <= source_systems
        return

    pytest.fail(f"unknown scenario kind: {kind!r}")


def test_scenario_catalog_covers_required_frs() -> None:
    """increment-15 coverage gate: all 7 NL questions + FR1-FR10/FR12/FR13."""
    frs = {scenario["fr"] for scenario in SCENARIOS}
    required = {
        "FR1",
        "FR2",
        "FR3",
        "FR4",
        "FR6",
        "FR8",
        "FR9",
        "FR10",
        "FR11",
        "FR12",
        "FR13",
    }
    assert required <= frs
    nl_ids = {scenario["id"] for scenario in SCENARIOS if scenario.get("fr") == "FR11"}
    assert len(nl_ids) == 7
