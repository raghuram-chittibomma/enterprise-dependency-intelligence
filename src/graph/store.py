"""The `GraphStore` Protocol -- the seam between the ingestion/query layers
and whichever graph backend is actually running (ADR-0001). Grows a method at
a time as each increment needs it; not every future query shape is speculated
here up front.
"""

from __future__ import annotations

from typing import Protocol

from src.graph.types import HealthCheckResult
from src.ontology.entities import NodeBase
from src.ontology.relationships import RelationshipBase


class GraphStore(Protocol):
    def health_check(self) -> HealthCheckResult:
        """Cheaply verify the backend is reachable and usable."""
        ...

    def bootstrap_schema(self) -> None:
        """Create any indexes/constraints the store needs (e.g. a uniqueness
        constraint on `id` per label) -- idempotent, safe to call every startup.
        """
        ...

    def upsert_node(self, label: str, node: NodeBase) -> None:
        """Create-or-update a node by its natural key (`node.id`) -- this is
        what makes ingestion idempotent (ADR-0002).
        """
        ...

    def upsert_relationship(
        self, rel_type: str, rel: RelationshipBase, source_label: str, target_label: str
    ) -> None:
        """Create-or-update a relationship between two already-upserted nodes."""
        ...

    def count_nodes(self, label: str | None = None) -> int: ...

    def count_relationships(self, rel_type: str | None = None) -> int: ...

    def get_all_nodes(self) -> list[dict]:
        """Every node in the graph as a flat dict of its properties plus a
        `label` key -- the read-everything escape hatch used by the
        data-quality checks (increment-5), which need to see the whole graph
        rather than one targeted query at a time.
        """
        ...

    def get_all_relationships(self) -> list[dict]:
        """Every relationship in the graph as a flat dict of its properties
        plus `rel_type`, `source_id`, `target_id` keys. See `get_all_nodes`.
        """
        ...

    def close(self) -> None: ...
