"""Technology / engine rationalization report (`ADR-0008`, FR26)."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from src.graph.queries import get_owning_team
from src.graph.store import GraphStore


@dataclass
class RationalizationBucket:
    key: str
    category: str  # technology | engine
    count: int
    criticality_mix: dict[str, int] = field(default_factory=dict)
    lifecycle_mix: dict[str, int] = field(default_factory=dict)
    owners: list[str] = field(default_factory=list)
    examples: list[tuple[str, str]] = field(default_factory=list)  # (id, name)


@dataclass(frozen=True)
class RationalizationReport:
    technology_buckets: list[RationalizationBucket]
    engine_buckets: list[RationalizationBucket]


def _mix_inc(mix: dict[str, int], value: str | None, default: str) -> None:
    key = (value or default).lower()
    mix[key] = mix.get(key, 0) + 1


def rationalize_technologies(store: GraphStore) -> RationalizationReport:
    tech_nodes: dict[str, list[dict]] = defaultdict(list)
    engine_nodes: dict[str, list[dict]] = defaultdict(list)

    for node in store.get_all_nodes():
        label = node.get("label")
        if label in {"Application", "Service"}:
            tech = (node.get("technology") or "").strip() or "(unset)"
            tech_nodes[tech].append(node)
        elif label == "Database":
            engine = (node.get("engine") or "").strip() or "(unset)"
            engine_nodes[engine].append(node)

    def build(buckets: dict[str, list[dict]], category: str) -> list[RationalizationBucket]:
        out: list[RationalizationBucket] = []
        for key, nodes in buckets.items():
            crit: dict[str, int] = {}
            life: dict[str, int] = {}
            owners: set[str] = set()
            examples: list[tuple[str, str]] = []
            for node in sorted(nodes, key=lambda n: n.get("name") or ""):
                _mix_inc(crit, node.get("criticality"), "unset")
                _mix_inc(life, node.get("lifecycle_status"), "active")
                owner = get_owning_team(store, node["id"])
                if owner:
                    owners.add(owner.name)
                if len(examples) < 5:
                    examples.append((node["id"], node["name"]))
            out.append(
                RationalizationBucket(
                    key=key,
                    category=category,
                    count=len(nodes),
                    criticality_mix=dict(sorted(crit.items())),
                    lifecycle_mix=dict(sorted(life.items())),
                    owners=sorted(owners),
                    examples=examples,
                )
            )
        out.sort(key=lambda b: (-b.count, b.key.lower()))
        return out

    return RationalizationReport(
        technology_buckets=build(tech_nodes, "technology"),
        engine_buckets=build(engine_nodes, "engine"),
    )
