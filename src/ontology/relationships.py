"""The 7 relationship types. See `docs/01_architecture/DATA_MODEL.md` for the
ontology rationale (including why `DEPENDS_ON` is intentionally never
persisted) and `ADR-0003-provenance-model.md` for the provenance fields.
"""

from __future__ import annotations

from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field

from src.ontology.entities import ALL_ENTITY_TYPES
from src.ontology.types import EvidenceType

_ALL_ENTITY_LABELS: frozenset[str] = frozenset(cls.__name__ for cls in ALL_ENTITY_TYPES)


class EndpointTypeError(ValueError):
    """Raised when a relationship is built between node types it doesn't allow."""


class RelationshipBase(BaseModel):
    """Common shape for every relationship in the graph.

    `source_id`/`target_id` reference `NodeBase.id` values (not Python
    object identity) — relationships are constructed after nodes are
    resolved, so this stays a plain data model with no graph-library
    dependency.
    """

    model_config = ConfigDict(extra="forbid")

    source_id: str = Field(min_length=1)
    target_id: str = Field(min_length=1)
    source_system: str = Field(min_length=1)
    source_record_id: str = Field(min_length=1)
    evidence_type: EvidenceType = EvidenceType.DOCUMENTED

    # Overridden by every subclass.
    REL_TYPE: ClassVar[str] = ""
    ALLOWED_SOURCE_LABELS: ClassVar[frozenset[str]] = frozenset()
    ALLOWED_TARGET_LABELS: ClassVar[frozenset[str]] = frozenset()

    @classmethod
    def rel_type(cls) -> str:
        """The Neo4j relationship type — matches `REL_TYPE` (e.g. `CONSUMES`)."""
        return cls.REL_TYPE

    @classmethod
    def validate_endpoints(cls, source_label: str, target_label: str) -> None:
        """Raise `EndpointTypeError` if the given node labels aren't allowed
        as this relationship's source/target. Ingestion must call this
        before writing any relationship — it's the enforcement point for the
        directed endpoint-type rules in `docs/01_architecture/DATA_MODEL.md`.
        """
        if source_label not in cls.ALLOWED_SOURCE_LABELS:
            raise EndpointTypeError(
                f"{cls.REL_TYPE} does not allow source label {source_label!r}; "
                f"allowed: {sorted(cls.ALLOWED_SOURCE_LABELS)}"
            )
        if target_label not in cls.ALLOWED_TARGET_LABELS:
            raise EndpointTypeError(
                f"{cls.REL_TYPE} does not allow target label {target_label!r}; "
                f"allowed: {sorted(cls.ALLOWED_TARGET_LABELS)}"
            )


class Consumes(RelationshipBase):
    """Synchronous functional dependency: source calls target to do its job."""

    REL_TYPE: ClassVar[str] = "CONSUMES"
    ALLOWED_SOURCE_LABELS: ClassVar[frozenset[str]] = frozenset({"Application", "Service", "API"})
    ALLOWED_TARGET_LABELS: ClassVar[frozenset[str]] = frozenset({"Service", "API"})


class ReadsFrom(RelationshipBase):
    REL_TYPE: ClassVar[str] = "READS_FROM"
    ALLOWED_SOURCE_LABELS: ClassVar[frozenset[str]] = frozenset(
        {"Application", "Service", "API", "DataPipeline", "Report"}
    )
    ALLOWED_TARGET_LABELS: ClassVar[frozenset[str]] = frozenset(
        {"Database", "API", "DataPipeline"}
    )


class WritesTo(RelationshipBase):
    REL_TYPE: ClassVar[str] = "WRITES_TO"
    ALLOWED_SOURCE_LABELS: ClassVar[frozenset[str]] = frozenset(
        {"Application", "Service", "API", "DataPipeline"}
    )
    ALLOWED_TARGET_LABELS: ClassVar[frozenset[str]] = frozenset({"Database", "DataPipeline"})


class IntegratesWith(RelationshipBase):
    REL_TYPE: ClassVar[str] = "INTEGRATES_WITH"
    ALLOWED_SOURCE_LABELS: ClassVar[frozenset[str]] = frozenset({"Application", "Service"})
    ALLOWED_TARGET_LABELS: ClassVar[frozenset[str]] = frozenset({"ExternalSystem"})

    # From the Integration Catalog source.
    integration_type: str | None = None
    protocol: str | None = None
    frequency: str | None = None


class Supports(RelationshipBase):
    REL_TYPE: ClassVar[str] = "SUPPORTS"
    ALLOWED_SOURCE_LABELS: ClassVar[frozenset[str]] = frozenset({"Application", "Service", "API"})
    ALLOWED_TARGET_LABELS: ClassVar[frozenset[str]] = frozenset({"BusinessCapability"})


class OwnedBy(RelationshipBase):
    """Many-to-one for MVP1: each entity has exactly one owning team
    (documented simplification — see `docs/01_architecture/DATA_MODEL.md`).
    """

    REL_TYPE: ClassVar[str] = "OWNED_BY"
    ALLOWED_SOURCE_LABELS: ClassVar[frozenset[str]] = _ALL_ENTITY_LABELS
    ALLOWED_TARGET_LABELS: ClassVar[frozenset[str]] = frozenset({"Team"})


class ReplacedBy(RelationshipBase):
    """One-to-one for MVP1: one successor per entity (documented
    simplification — see `docs/01_architecture/DATA_MODEL.md`).
    """

    REL_TYPE: ClassVar[str] = "REPLACED_BY"
    ALLOWED_SOURCE_LABELS: ClassVar[frozenset[str]] = frozenset({"Application", "API"})
    ALLOWED_TARGET_LABELS: ClassVar[frozenset[str]] = frozenset({"Application", "API"})
