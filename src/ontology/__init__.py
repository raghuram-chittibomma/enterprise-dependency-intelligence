"""The Enterprise Dependency Intelligence ontology.

9 node types + 7 relationship types, per `docs/01_architecture/DATA_MODEL.md`.
This package is the single source of truth for the shape of the graph — the
ingestion pipeline, query layer, and NL query layer all build on these models
rather than each defining their own notion of what an "Application" is.
"""

from src.ontology.entities import (
    API,
    Application,
    BusinessCapability,
    Database,
    DataPipeline,
    ExternalSystem,
    NodeBase,
    Report,
    Service,
    Team,
)
from src.ontology.registry import NODE_TYPES, RELATIONSHIP_TYPES
from src.ontology.relationships import (
    Consumes,
    IntegratesWith,
    OwnedBy,
    ReadsFrom,
    RelationshipBase,
    ReplacedBy,
    Supports,
    WritesTo,
)
from src.ontology.types import Criticality, EvidenceType, LifecycleStatus

__all__ = [
    "API",
    "NODE_TYPES",
    "RELATIONSHIP_TYPES",
    "Application",
    "BusinessCapability",
    "Consumes",
    "Criticality",
    "Database",
    "DataPipeline",
    "EvidenceType",
    "ExternalSystem",
    "IntegratesWith",
    "LifecycleStatus",
    "NodeBase",
    "OwnedBy",
    "ReadsFrom",
    "RelationshipBase",
    "ReplacedBy",
    "Report",
    "Service",
    "Supports",
    "Team",
    "WritesTo",
]
