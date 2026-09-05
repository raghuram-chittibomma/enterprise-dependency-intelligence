"""Result shapes for MVP4 Agentic Investigation (`ADR-0007`)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from src.graph.queries import EntityRef
from src.nlquery.answering import EvidenceDocChunk, EvidenceEdge

InvestigationStatus = Literal[
    "answered",
    "disabled",
    "not_found",
    "ambiguous",
    "insufficient_evidence",
    "missing_api_key",
]


@dataclass(frozen=True)
class InvestigationStep:
    """Compact step-trace entry (FR22) — not a free-form agent diary."""

    phase: Literal["skeleton", "adaptive", "report"]
    tool: str
    args_summary: str
    result_summary: str


@dataclass
class InvestigationResult:
    question: str
    status: InvestigationStatus
    summary: str
    findings: list[str] = field(default_factory=list)
    seed_entity: EntityRef | None = None
    evidence: list[EvidenceEdge] = field(default_factory=list)
    doc_evidence: list[EvidenceDocChunk] = field(default_factory=list)
    steps: list[InvestigationStep] = field(default_factory=list)
