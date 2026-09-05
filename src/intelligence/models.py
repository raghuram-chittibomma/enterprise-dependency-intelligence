"""Shared result shapes for MVP5 intelligence (`ADR-0008`)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

RiskBand = Literal["low", "medium", "high", "critical"]


@dataclass(frozen=True)
class EvidenceRef:
    kind: str  # property | entity | edge | unresolved
    label: str
    entity_id: str | None = None
    detail: str | None = None


@dataclass(frozen=True)
class RiskFactor:
    id: str
    label: str
    points: int
    evidence: list[EvidenceRef] = field(default_factory=list)


@dataclass(frozen=True)
class RiskAssessment:
    entity_id: str
    entity_name: str
    entity_label: str
    score: int
    band: RiskBand
    factors: list[RiskFactor]
    narrative: str | None = None
