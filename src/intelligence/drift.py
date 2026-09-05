"""Drift signal detection (`ADR-0008`, FR25)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from src.graph.queries import get_direct_dependencies
from src.graph.store import GraphStore
from src.ingestion.pipeline import DEFAULT_UNRESOLVED_PATH

DriftSeverity = Literal["high", "medium", "low"]
DriftKind = Literal["lifecycle", "replacement", "resolution"]


@dataclass(frozen=True)
class DriftSignal:
    kind: DriftKind
    severity: DriftSeverity
    title: str
    detail: str
    entity_id: str | None = None
    entity_name: str | None = None
    related_ids: tuple[str, ...] = ()


def _inbound_consumers(store: GraphStore, entity_id: str) -> list[tuple[str, str]]:
    deps = get_direct_dependencies(store, entity_id)
    if deps is None:
        return []
    return [(e.entity.id, e.entity.name) for e in deps.downstream]


def detect_lifecycle_drift(store: GraphStore) -> list[DriftSignal]:
    signals: list[DriftSignal] = []
    for node in store.get_all_nodes():
        if node.get("label") in {"Document", "Team", "BusinessCapability"}:
            continue
        life = (node.get("lifecycle_status") or "active").lower()
        if life not in {"deprecated", "retired"}:
            continue
        consumers = _inbound_consumers(store, node["id"])
        if not consumers:
            continue
        names = ", ".join(n for _, n in consumers[:5])
        more = f" (+{len(consumers) - 5} more)" if len(consumers) > 5 else ""
        signals.append(
            DriftSignal(
                kind="lifecycle",
                severity="high" if life == "deprecated" else "medium",
                title=f"{node['name']} is {life} but still consumed",
                detail=f"Inbound dependents: {names}{more}",
                entity_id=node["id"],
                entity_name=node["name"],
                related_ids=tuple(i for i, _ in consumers),
            )
        )
    signals.sort(key=lambda s: (s.severity != "high", s.entity_name or ""))
    return signals


def detect_replacement_drift(store: GraphStore) -> list[DriftSignal]:
    signals: list[DriftSignal] = []
    node_by_id = {n["id"]: n for n in store.get_all_nodes()}
    for rel in store.get_all_relationships():
        if rel.get("rel_type") != "REPLACED_BY":
            continue
        source_id = rel["source_id"]
        source = node_by_id.get(source_id)
        if source is None:
            continue
        consumers = _inbound_consumers(store, source_id)
        if not consumers:
            continue
        successor = node_by_id.get(rel["target_id"])
        succ_name = successor["name"] if successor else rel["target_id"]
        names = ", ".join(n for _, n in consumers[:5])
        signals.append(
            DriftSignal(
                kind="replacement",
                severity="high",
                title=f"{source['name']} has REPLACED_BY → {succ_name} but still has consumers",
                detail=f"Still depended on by: {names}",
                entity_id=source_id,
                entity_name=source["name"],
                related_ids=tuple(i for i, _ in consumers),
            )
        )
    signals.sort(key=lambda s: s.entity_name or "")
    return signals


def detect_resolution_drift(
    unresolved_path: Path | None = DEFAULT_UNRESOLVED_PATH,
) -> list[DriftSignal]:
    path = unresolved_path or DEFAULT_UNRESOLVED_PATH
    if not path.exists():
        return []
    try:
        rows = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return [
            DriftSignal(
                kind="resolution",
                severity="low",
                title="Unresolved queue unreadable",
                detail=str(path),
            )
        ]
    if not isinstance(rows, list) or not rows:
        return []
    signals: list[DriftSignal] = []
    for row in rows[:50]:
        if not isinstance(row, dict):
            continue
        name = str(row.get("name") or "unknown")
        etype = str(row.get("entity_type") or "?")
        src = str(row.get("referenced_by_source") or "?")
        rid = str(row.get("referenced_by_record_id") or "?")
        signals.append(
            DriftSignal(
                kind="resolution",
                severity="medium",
                title=f"Unresolved {etype} reference: {name}",
                detail=f"Referenced by {src} record {rid}",
            )
        )
    return signals


def detect_drift(
    store: GraphStore,
    *,
    unresolved_path: Path | None = DEFAULT_UNRESOLVED_PATH,
) -> list[DriftSignal]:
    """Combine lifecycle, replacement, and resolution drift signals."""
    return (
        detect_lifecycle_drift(store)
        + detect_replacement_drift(store)
        + detect_resolution_drift(unresolved_path)
    )
