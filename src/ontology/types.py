"""Shared enums used across node and relationship models."""

from __future__ import annotations

from enum import StrEnum


class LifecycleStatus(StrEnum):
    """A node's position in its lifecycle. See `docs/01_architecture/DATA_MODEL.md`."""

    ACTIVE = "active"
    DEPRECATED = "deprecated"
    RETIRED = "retired"
    PLANNED = "planned"


class Criticality(StrEnum):
    """Business criticality, where applicable (not every entity type needs one)."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EvidenceType(StrEnum):
    """Whether a relationship was explicitly stated by a source or derived.

    MVP1 ingestion only ever writes DOCUMENTED. INFERRED is reserved for
    MVP2+ Graph RAG-derived edges (ADR-0003).
    """

    DOCUMENTED = "documented"
    INFERRED = "inferred"
