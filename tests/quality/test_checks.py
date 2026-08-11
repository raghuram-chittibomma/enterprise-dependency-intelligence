"""Unit tests for each data-quality invariant (increment-5), exercised with
small hand-written fixtures per `docs/02_testing/TEST_STRATEGY.md`'s test
data policy -- not the full generated dataset (that's covered separately in
`test_ingested_graph_quality.py`).
"""

from __future__ import annotations

from src.quality.checks import (
    QualityReport,
    check_no_duplicate_names_per_label,
    check_no_duplicate_natural_keys,
    check_no_orphan_nodes,
    check_referential_consistency,
    check_required_provenance_fields,
    run_all_checks,
)


def _node(node_id: str, label: str = "Application", name: str | None = None, **overrides) -> dict:
    base = {
        "id": node_id,
        "label": label,
        "name": name or node_id,
        "source_system": "cmdb",
        "source_record_id": "APP-001",
        "ingested_at": "2026-08-11T00:00:00Z",
    }
    base.update(overrides)
    return base


def _rel(source_id: str, target_id: str, rel_type: str = "CONSUMES", **overrides) -> dict:
    base = {
        "source_id": source_id,
        "target_id": target_id,
        "rel_type": rel_type,
        "source_system": "api_catalog",
        "source_record_id": "API-001",
        "evidence_type": "documented",
    }
    base.update(overrides)
    return base


class TestNoDuplicateNaturalKeys:
    def test_passes_when_all_ids_unique(self) -> None:
        nodes = [_node("app-1"), _node("app-2")]
        assert check_no_duplicate_natural_keys(nodes) == []

    def test_flags_a_repeated_id(self) -> None:
        nodes = [_node("app-1", name="Storefront"), _node("app-1", name="Storefront Duplicate")]
        issues = check_no_duplicate_natural_keys(nodes)
        assert len(issues) == 1
        assert issues[0].severity == "error"
        assert issues[0].subject == "app-1"


class TestNoDuplicateNamesPerLabel:
    def test_passes_for_distinct_names(self) -> None:
        nodes = [_node("app-1", name="Storefront"), _node("app-2", name="Checkout")]
        assert check_no_duplicate_names_per_label(nodes) == []

    def test_flags_same_name_same_label_case_insensitive(self) -> None:
        nodes = [_node("app-1", name="Storefront"), _node("app-2", name="storefront ")]
        issues = check_no_duplicate_names_per_label(nodes)
        assert len(issues) == 1
        assert issues[0].severity == "warning"

    def test_allows_same_name_across_different_labels(self) -> None:
        nodes = [
            _node("app-1", label="Application", name="Orders"),
            _node("svc-1", label="Service", name="Orders"),
        ]
        assert check_no_duplicate_names_per_label(nodes) == []


class TestReferentialConsistency:
    def test_passes_when_both_endpoints_exist(self) -> None:
        nodes = [_node("app-1"), _node("api-1", label="API")]
        rels = [_rel("app-1", "api-1")]
        assert check_referential_consistency(nodes, rels) == []

    def test_flags_dangling_target(self) -> None:
        nodes = [_node("app-1")]
        rels = [_rel("app-1", "api-does-not-exist")]
        issues = check_referential_consistency(nodes, rels)
        assert len(issues) == 1
        assert "target" in issues[0].message

    def test_flags_dangling_source(self) -> None:
        nodes = [_node("api-1", label="API")]
        rels = [_rel("app-does-not-exist", "api-1")]
        issues = check_referential_consistency(nodes, rels)
        assert len(issues) == 1
        assert "source" in issues[0].message


class TestNoOrphanNodes:
    def test_passes_when_every_node_has_a_relationship(self) -> None:
        nodes = [_node("app-1"), _node("api-1", label="API")]
        rels = [_rel("app-1", "api-1")]
        assert check_no_orphan_nodes(nodes, rels) == []

    def test_flags_a_node_with_zero_relationships(self) -> None:
        nodes = [_node("app-1"), _node("app-2")]
        rels: list[dict] = []
        issues = check_no_orphan_nodes(nodes, rels)
        assert {issue.subject for issue in issues} == {"app-1", "app-2"}

    def test_a_node_only_appearing_as_a_target_is_not_orphaned(self) -> None:
        nodes = [_node("app-1"), _node("api-1", label="API")]
        rels = [_rel("app-1", "api-1")]
        issues = check_no_orphan_nodes(nodes, rels)
        assert issues == []


class TestRequiredProvenanceFields:
    def test_passes_with_full_provenance(self) -> None:
        nodes = [_node("app-1")]
        rels = [_rel("app-1", "app-1")]
        assert check_required_provenance_fields(nodes, rels) == []

    def test_flags_a_node_missing_source_system(self) -> None:
        nodes = [_node("app-1", source_system="")]
        issues = check_required_provenance_fields(nodes, [])
        assert len(issues) == 1
        assert "source_system" in issues[0].message

    def test_flags_a_node_with_missing_key_entirely(self) -> None:
        node = _node("app-1")
        del node["ingested_at"]
        issues = check_required_provenance_fields([node], [])
        assert len(issues) == 1
        assert "ingested_at" in issues[0].message

    def test_flags_a_relationship_missing_evidence_type(self) -> None:
        rels = [_rel("app-1", "app-2", evidence_type=None)]
        issues = check_required_provenance_fields([], rels)
        assert len(issues) == 1
        assert "evidence_type" in issues[0].message


class TestRunAllChecks:
    def test_clean_graph_reports_ok(self) -> None:
        nodes = [
            _node("app-1", name="Storefront"),
            _node("api-1", label="API", name="Customer API"),
        ]
        rels = [_rel("app-1", "api-1")]
        report = run_all_checks(nodes, rels)
        assert isinstance(report, QualityReport)
        assert report.ok
        assert report.issues == []

    def test_a_single_error_makes_the_report_not_ok(self) -> None:
        nodes = [_node("app-1")]
        rels = [_rel("app-1", "missing-target")]
        report = run_all_checks(nodes, rels)
        assert not report.ok
        assert len(report.errors()) >= 1

    def test_warnings_alone_do_not_make_the_report_not_ok(self) -> None:
        nodes = [_node("app-1", name="Storefront"), _node("app-2", name="Storefront")]
        report = run_all_checks(nodes, [])
        # duplicate-name is a warning, but both nodes are still orphans (errors) here --
        # isolate the warning-only case by also giving them a relationship each.
        rels = [_rel("app-1", "app-2")]
        report = run_all_checks(nodes, rels)
        assert report.ok
        assert report.warnings()
        assert report.errors() == []
