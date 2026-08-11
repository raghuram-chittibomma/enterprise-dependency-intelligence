"""Pure functions implementing each data-quality invariant from
`docs/02_testing/TEST_STRATEGY.md`. Each check takes plain dicts (as
returned by `GraphStore.get_all_nodes`/`get_all_relationships`), not a live
store connection, so they're cheap to unit test with small hand-written
fixtures and are backend-agnostic (Neo4j or the fallback store).
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Nodes missing any of these are a broken provenance promise (ADR-0003).
REQUIRED_NODE_PROVENANCE_FIELDS = ("source_system", "source_record_id", "ingested_at")
REQUIRED_REL_PROVENANCE_FIELDS = ("source_system", "source_record_id", "evidence_type")


@dataclass(frozen=True)
class QualityIssue:
    check: str
    severity: str  # "error" (breaks the trust promise) or "warning" (worth a look)
    subject: str  # node id, or "source_id -> target_id" for a relationship
    message: str


@dataclass
class QualityReport:
    issues: list[QualityIssue] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not any(issue.severity == "error" for issue in self.issues)

    def errors(self) -> list[QualityIssue]:
        return [issue for issue in self.issues if issue.severity == "error"]

    def warnings(self) -> list[QualityIssue]:
        return [issue for issue in self.issues if issue.severity == "warning"]


def _is_blank(value: object) -> bool:
    """A provenance value counts as missing if the key is absent, `None`, or
    an empty/whitespace-only string -- not just structurally absent.
    """
    return value is None or (isinstance(value, str) and not value.strip())


def check_no_duplicate_natural_keys(nodes: list[dict]) -> list[QualityIssue]:
    """Every node's `id` (the natural key, per `DATA_MODEL.md`) must be
    globally unique. Structurally this should be unenforceable given
    `MERGE`/`PRIMARY KEY` semantics in both backends -- this check exists as
    a defensive invariant, catching a store-layer regression rather than an
    ingestion-logic bug.
    """
    seen: dict[str, int] = {}
    for node in nodes:
        seen[node["id"]] = seen.get(node["id"], 0) + 1
    return [
        QualityIssue(
            check="no_duplicate_natural_keys",
            severity="error",
            subject=node_id,
            message=f"id {node_id!r} appears on {count} nodes; ids must be globally unique",
        )
        for node_id, count in seen.items()
        if count > 1
    ]


def check_no_duplicate_names_per_label(nodes: list[dict]) -> list[QualityIssue]:
    """Two nodes of the same label with the same name (case-insensitive)
    usually means entity resolution (ADR-0002) failed to merge two records
    that referred to the same real-world thing -- worth a look, but not
    necessarily a hard error (two distinct real entities could coincidentally
    share a name), hence `warning` rather than `error`.
    """
    seen: dict[tuple[str, str], list[str]] = {}
    for node in nodes:
        key = (node["label"], node["name"].strip().lower())
        seen.setdefault(key, []).append(node["id"])
    issues = []
    for (label, normalized_name), ids in seen.items():
        if len(ids) > 1:
            issues.append(
                QualityIssue(
                    check="no_duplicate_names_per_label",
                    severity="warning",
                    subject=", ".join(sorted(ids)),
                    message=(
                        f"{len(ids)} {label} nodes share the name "
                        f"{normalized_name!r}: {sorted(ids)}"
                    ),
                )
            )
    return issues


def check_referential_consistency(
    nodes: list[dict], relationships: list[dict]
) -> list[QualityIssue]:
    """Every relationship endpoint must resolve to a node that actually
    exists -- a dangling endpoint would mean the graph asserts a dependency
    that traces to nothing, which is exactly what ADR-0003's trust promise
    forbids.
    """
    node_ids = {node["id"] for node in nodes}
    issues = []
    for rel in relationships:
        for endpoint_field, role in (("source_id", "source"), ("target_id", "target")):
            endpoint_id = rel[endpoint_field]
            if endpoint_id not in node_ids:
                issues.append(
                    QualityIssue(
                        check="referential_consistency",
                        severity="error",
                        subject=f"{rel['source_id']} -> {rel['target_id']}",
                        message=(
                            f"{rel['rel_type']} relationship's {role} {endpoint_id!r} "
                            "does not match any existing node id"
                        ),
                    )
                )
    return issues


def check_no_orphan_nodes(nodes: list[dict], relationships: list[dict]) -> list[QualityIssue]:
    """Every node should participate in at least one relationship (as either
    endpoint) -- an entity with zero connections in a *dependency* graph is
    either a modeling gap (missing edge) or dead data that shouldn't have
    been ingested.
    """
    connected_ids: set[str] = set()
    for rel in relationships:
        connected_ids.add(rel["source_id"])
        connected_ids.add(rel["target_id"])
    return [
        QualityIssue(
            check="no_orphan_nodes",
            severity="error",
            subject=node["id"],
            message=(
                f"{node['label']} node {node['id']!r} ({node['name']!r}) has zero relationships"
            ),
        )
        for node in nodes
        if node["id"] not in connected_ids
    ]


def check_required_provenance_fields(
    nodes: list[dict], relationships: list[dict]
) -> list[QualityIssue]:
    """Every node and relationship must carry the full provenance triple/quad
    from ADR-0003 -- this is what makes the FR12 evidence panel and every NL
    query answer traceable rather than an unverifiable assertion.
    """
    issues = []
    for node in nodes:
        for prov_field in REQUIRED_NODE_PROVENANCE_FIELDS:
            if _is_blank(node.get(prov_field)):
                issues.append(
                    QualityIssue(
                        check="required_provenance_fields",
                        severity="error",
                        subject=node["id"],
                        message=f"{node['label']} node {node['id']!r} is missing '{prov_field}'",
                    )
                )
    for rel in relationships:
        for prov_field in REQUIRED_REL_PROVENANCE_FIELDS:
            if _is_blank(rel.get(prov_field)):
                issues.append(
                    QualityIssue(
                        check="required_provenance_fields",
                        severity="error",
                        subject=f"{rel['source_id']} -> {rel['target_id']}",
                        message=(
                            f"{rel['rel_type']} relationship "
                            f"{rel['source_id']!r} -> {rel['target_id']!r} "
                            f"is missing '{prov_field}'"
                        ),
                    )
                )
    return issues


def run_all_checks(nodes: list[dict], relationships: list[dict]) -> QualityReport:
    """Run every data-quality invariant against a snapshot of the graph
    (as returned by `GraphStore.get_all_nodes`/`get_all_relationships`).
    """
    issues: list[QualityIssue] = []
    issues += check_no_duplicate_natural_keys(nodes)
    issues += check_no_duplicate_names_per_label(nodes)
    issues += check_referential_consistency(nodes, relationships)
    issues += check_no_orphan_nodes(nodes, relationships)
    issues += check_required_provenance_fields(nodes, relationships)
    return QualityReport(issues=issues)
