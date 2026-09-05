"""The 10 node types. See `docs/01_architecture/DATA_MODEL.md` for the ontology
rationale and `docs/01_architecture/DECISIONS/ADR-0003-provenance-model.md` for
why every node carries provenance fields.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from src.ontology.types import Criticality, LifecycleStatus


class NodeBase(BaseModel):
    """Common shape for every node in the graph.

    `id` is a stable natural key (see DATA_MODEL.md's Identity strategy),
    never an opaque generated id — this is what makes ingestion idempotent.
    """

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    description: str = ""
    lifecycle_status: LifecycleStatus = LifecycleStatus.ACTIVE
    criticality: Criticality | None = None
    source_system: str = Field(min_length=1)
    source_record_id: str = Field(min_length=1)
    ingested_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @classmethod
    def label(cls) -> str:
        """The Neo4j node label for this type — matches the class name 1:1."""
        return cls.__name__


class BusinessCapability(NodeBase):
    capability_area: str = Field(min_length=1)


class _TechEnvironmentFields(BaseModel):
    technology: str = Field(min_length=1)
    environment: str = Field(min_length=1)


class Application(NodeBase, _TechEnvironmentFields):
    pass


class Service(NodeBase, _TechEnvironmentFields):
    pass


class API(NodeBase):
    version: str = Field(min_length=1)
    protocol: str = Field(min_length=1)
    # Display-only property naming the app/service that implements this API.
    # Intentionally NOT a relationship — no FR traverses it (see DATA_MODEL.md).
    implementing_application: str | None = None


class Database(NodeBase):
    engine: str = Field(min_length=1)
    key_tables: list[str] = Field(default_factory=list)


class DataPipeline(NodeBase):
    pipeline_type: Literal["etl", "batch_job"]
    schedule: str | None = None


class Report(NodeBase):
    audience: str = Field(min_length=1)
    refresh_frequency: str = Field(min_length=1)


class ExternalSystem(NodeBase):
    vendor: str = Field(min_length=1)
    category: str = Field(min_length=1)


class Team(NodeBase):
    business_area: str = Field(min_length=1)


class Document(NodeBase):
    """Unstructured architecture / design note (MVP3 Hybrid Doc RAG)."""

    path: str = Field(min_length=1)
    doc_type: str = Field(default="architecture_note", min_length=1)


# Node types that may participate as the source of an OWNED_BY relationship
# (i.e. every entity type) — defined here, next to the entity classes
# themselves, and re-exported via registry.py for relationship validation.
ALL_ENTITY_TYPES: tuple[type[NodeBase], ...] = (
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
