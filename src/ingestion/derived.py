"""Helper for node types that don't have their own dedicated source file --
`BusinessCapability` (derived from CMDB/API Catalog `business_capability`
fields) and `ExternalSystem` (derived from the Integration Catalog's target
system columns). Both are "create on first sight, reuse after" -- this
function is the one place that pattern lives.
"""

from __future__ import annotations

from collections.abc import Callable

from src.ingestion.identity import make_id
from src.ingestion.resolution import EntityResolver
from src.ontology.entities import NodeBase


def get_or_create(
    resolver: EntityResolver,
    entity_type: str,
    label: str,
    name: str,
    source_system: str,
    build: Callable[[str], NodeBase],
) -> tuple[str, NodeBase | None]:
    """Returns `(id, node)` where `node` is `None` if the entity already
    existed (nothing new to upsert) or the newly-built node otherwise.
    `build(id_)` must construct the node with that exact id.
    """
    existing = resolver.lookup_exact(entity_type, name)
    if existing is not None:
        return existing, None

    node_id = make_id(label, source_system, name)
    node = build(node_id)
    resolver.register(entity_type, name, node_id)
    return node_id, node
