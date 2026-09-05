"""Label/rel-type -> model class lookups, used by ingestion and the query
layer so neither has to hardcode the type list in more than one place.
"""

from __future__ import annotations

from src.ontology.entities import (
    API,
    Application,
    BusinessCapability,
    Database,
    DataPipeline,
    Document,
    ExternalSystem,
    NodeBase,
    Report,
    Service,
    Team,
)
from src.ontology.relationships import (
    Consumes,
    DocumentedBy,
    IntegratesWith,
    OwnedBy,
    ReadsFrom,
    RelationshipBase,
    ReplacedBy,
    Supports,
    WritesTo,
)

NODE_TYPES: dict[str, type[NodeBase]] = {
    cls.__name__: cls
    for cls in (
        Application,
        Service,
        API,
        Database,
        DataPipeline,
        Report,
        ExternalSystem,
        Team,
        BusinessCapability,
        Document,
    )
}

RELATIONSHIP_TYPES: dict[str, type[RelationshipBase]] = {
    cls.REL_TYPE: cls
    for cls in (
        Consumes,
        ReadsFrom,
        WritesTo,
        IntegratesWith,
        Supports,
        OwnedBy,
        ReplacedBy,
        DocumentedBy,
    )
}

assert len(NODE_TYPES) == 10, "Ontology drift: expected exactly 10 node types."
assert len(RELATIONSHIP_TYPES) == 8, "Ontology drift: expected exactly 8 relationship types."
