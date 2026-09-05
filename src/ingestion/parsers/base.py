"""Shared shapes for the `SourceParser` implementations (the
`source_parser` extension point, `docs/01_architecture/ARCHITECTURE.md`).

Each parser module exposes `read(path)` (file -> raw rows) and two pure
functions that turn raw rows into ontology objects: `build_nodes(rows)` and
`build_relationships(rows, resolver)`. Splitting file I/O from graph-building
means the graph-building logic is unit-testable with plain dicts, no fixture
files required.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.ontology.relationships import RelationshipBase

# The "type" strings used throughout the source files map 1:1 to node labels.
TYPE_TO_LABEL: dict[str, str] = {
    "application": "Application",
    "service": "Service",
    "api": "API",
    "database": "Database",
    "data_pipeline": "DataPipeline",
    "report": "Report",
    "external_system": "ExternalSystem",
    "team": "Team",
    "business_capability": "BusinessCapability",
    "document": "Document",
}


@dataclass
class ParsedRelationship:
    """A relationship instance plus the node labels its endpoints resolved
    to -- the graph store needs both labels to write a typed edge, and a
    relationship instance alone doesn't carry them (it only carries ids).
    """

    relationship: RelationshipBase
    rel_type: str
    source_label: str
    target_label: str
