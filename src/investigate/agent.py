"""Bounded LLM tool loop + report synthesis for Investigate (`ADR-0007`)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Protocol

from src.graph.queries import EntityRef
from src.graph.store import GraphStore
from src.investigate.config import (
    agentic_max_tool_calls,
    openai_api_key,
    openai_model,
)
from src.investigate.models import InvestigationResult, InvestigationStep
from src.investigate.tools import TOOL_NAMES, EvidenceBundle, run_skeleton, run_tool
from src.nlquery.answering import EvidenceDocChunk, EvidenceEdge
from src.nlquery.llm import OpenAIChatClient
from src.nlquery.resolution import resolve_entity

MISSING_KEY_TEXT = (
    "Agentic Investigation is enabled, but OPENAI_API_KEY is not set. "
    "Closed Ask templates still work; set the key to enable Investigate."
)

DISABLED_TEXT = (
    "Agentic Investigation is disabled. Set AGENTIC_INVESTIGATION_ENABLED=true "
    "and OPENAI_API_KEY to run multi-step reports."
)

INSUFFICIENT_TEXT = (
    "Insufficient gathered evidence to produce a grounded investigation report "
    "without guessing."
)

PLANNER_SYSTEM = """You are planning the next allowlisted investigation tool call.
You may only choose from: traverse, find_paths, owners_rollup, capabilities_rollup,
doc_search, entity_detail. Reply with JSON only:
{"tool":"<name>|null","args":{...},"done":true|false}
If enough evidence exists, set done=true and tool=null.
Rules:
- traverse args: entity_id (optional), direction upstream|downstream, max_depth <=4
- find_paths args: other_entity_name (required)
- owners_rollup / capabilities_rollup args: entity_id optional, max_depth optional
- doc_search args: query
- entity_detail args: entity_id (must already appear in evidence ids)
Prefer at most one tool per response.
"""

REPORT_SYSTEM = """You write Meridian Retail Group dependency investigation reports.
Use ONLY the provided evidence JSON (edges and document_chunks). Reply JSON only:
{"status":"answered"|"insufficient_evidence","summary":"...","findings":["..."],
 "citations":[{"source_id":"...","target_id":"...","rel_type":"..."}],
 "doc_citations":[{"document_id":"...","chunk_id":"..."}]}
Every citation must match evidence exactly. Prefer fewer precise citations.
If evidence cannot support the question, status=insufficient_evidence.
"""


class ChatClient(Protocol):
    def complete(self, *, system: str, user: str) -> str: ...


@dataclass
class ScriptedClient:
    """Deterministic fake client for tests: planner replies then report reply."""

    replies: list[str]
    _i: int = 0

    def complete(self, *, system: str, user: str) -> str:
        if self._i >= len(self.replies):
            return json.dumps({"status": "insufficient_evidence", "summary": INSUFFICIENT_TEXT, "findings": [], "citations": [], "doc_citations": []})
        text = self.replies[self._i]
        self._i += 1
        return text


def _parse_json(raw: str) -> dict:
    text = raw.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1)
    else:
        start, end = text.find("{"), text.rfind("}")
        if start >= 0 and end > start:
            text = text[start : end + 1]
    return json.loads(text)


def _evidence_payload(bundle: EvidenceBundle, seed: EntityRef, question: str) -> str:
    return json.dumps(
        {
            "question": question,
            "seed": {"id": seed.id, "label": seed.label, "name": seed.name},
            "entity_ids": sorted(bundle.entity_ids),
            "edges": [
                {
                    "source_id": e.source_id,
                    "source_name": e.source_name,
                    "rel_type": e.rel_type,
                    "target_id": e.target_id,
                    "target_name": e.target_name,
                }
                for e in bundle.edges
            ],
            "document_chunks": [
                {
                    "document_id": d.document_id,
                    "document_name": d.document_name,
                    "chunk_id": d.chunk_id,
                    "text": d.text[:500],
                }
                for d in bundle.docs
            ],
            "allowlisted_tools": sorted(TOOL_NAMES),
        },
        ensure_ascii=False,
        indent=2,
    )


def _filter_citations(
    citations: list, bundle: EvidenceBundle
) -> list[EvidenceEdge]:
    edge_by_key = {(e.source_id, e.target_id, e.rel_type): e for e in bundle.edges}
    out: list[EvidenceEdge] = []
    seen: set[tuple[str, str, str]] = set()
    for citation in citations or []:
        try:
            key = (citation["source_id"], citation["target_id"], citation["rel_type"])
        except (KeyError, TypeError):
            continue
        edge = edge_by_key.get(key)
        if edge is None or key in seen:
            continue
        seen.add(key)
        out.append(edge)
    return out


def _filter_doc_citations(
    citations: list, bundle: EvidenceBundle
) -> list[EvidenceDocChunk]:
    by_key = {(d.document_id, d.chunk_id): d for d in bundle.docs}
    out: list[EvidenceDocChunk] = []
    seen: set[tuple[str, str]] = set()
    for citation in citations or []:
        try:
            key = (citation["document_id"], citation["chunk_id"])
        except (KeyError, TypeError):
            continue
        doc = by_key.get(key)
        if doc is None or key in seen:
            continue
        seen.add(key)
        out.append(doc)
    return out


# Seed resolution prefers tech entities over Documents (MVP3 docs share names).
_SEED_TECH_LABELS = frozenset(
    {
        "Application",
        "API",
        "Service",
        "Database",
        "DataPipeline",
        "ExternalSystem",
        "Team",
        "BusinessCapability",
        "Integration",
    }
)

_SEED_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "the",
        "and",
        "or",
        "of",
        "to",
        "for",
        "in",
        "on",
        "at",
        "by",
        "from",
        "with",
        "what",
        "which",
        "who",
        "whom",
        "whose",
        "where",
        "when",
        "why",
        "how",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "will",
        "would",
        "could",
        "should",
        "may",
        "might",
        "can",
        "we",
        "i",
        "you",
        "they",
        "it",
        "our",
        "if",
        "about",
        "please",
        "tell",
        "show",
        "me",
        "us",
        "this",
        "that",
        "these",
        "those",
        "any",
        "all",
        "impact",
        "impacts",
        "retire",
        "retiring",
        "retired",
        "change",
        "break",
        "breaks",
        "depend",
        "depends",
        "dependency",
    }
)


def _phrase_candidates(question: str) -> list[str]:
    """Contiguous token n-grams for fuzzy seed resolve (longest first)."""
    tokens = re.findall(r"[A-Za-z0-9][A-Za-z0-9._-]*", question)
    if not tokens:
        return []
    phrases: list[str] = []
    seen: set[str] = set()
    for n in range(min(6, len(tokens)), 0, -1):
        for i in range(len(tokens) - n + 1):
            chunk = tokens[i : i + n]
            if all(t.lower() in _SEED_STOPWORDS for t in chunk):
                continue
            if n == 1 and chunk[0].lower() in _SEED_STOPWORDS:
                continue
            phrase = " ".join(chunk)
            key = phrase.lower()
            if key in seen:
                continue
            seen.add(key)
            phrases.append(phrase)
    return phrases


def _resolve_seed(store: GraphStore, question: str) -> tuple[EntityRef | None, str, bool]:
    """Return (entity, unresolved_name, ambiguous).

    Exact graph-name substrings first, then fuzzy phrase resolve via
    ``resolve_entity`` (excludes Documents so \"customer api\" resolves to the
    API rather than tying with design notes).
    """
    from src.nlquery.graphrag import _mention_candidates

    nodes = store.get_all_nodes()
    tech_nodes = [n for n in nodes if n.get("label") != "Document"]
    first_ambiguous: str | None = None

    for name in _mention_candidates(question, tech_nodes):
        result = resolve_entity(store, name, allowed_labels=_SEED_TECH_LABELS)
        if result.entity is not None:
            return result.entity, name, False
        if result.ambiguous and first_ambiguous is None:
            first_ambiguous = name

    for phrase in _phrase_candidates(question):
        result = resolve_entity(store, phrase, allowed_labels=_SEED_TECH_LABELS)
        if result.entity is not None:
            return result.entity, phrase, False
        if result.ambiguous and first_ambiguous is None:
            first_ambiguous = phrase

    if first_ambiguous is not None:
        return None, first_ambiguous, True
    return None, question.strip()[:80] or "the question", False


def run_investigation(
    store: GraphStore,
    question: str,
    *,
    client: ChatClient | None = None,
    max_tool_calls: int | None = None,
) -> InvestigationResult:
    """Public Investigate entry — Ask path stays untouched."""
    q = question.strip()
    if not q:
        return InvestigationResult(question=question, status="insufficient_evidence", summary=INSUFFICIENT_TEXT)

    seed, unresolved, ambiguous = _resolve_seed(store, q)
    if ambiguous:
        return InvestigationResult(
            question=q,
            status="ambiguous",
            summary=(
                f'"{unresolved}" matches more than one entity and I can\'t tell which '
                "one you mean -- try a more specific name."
            ),
        )
    if seed is None:
        return InvestigationResult(
            question=q,
            status="not_found",
            summary=f'I couldn\'t find an entity matching "{unresolved}" in the graph.',
        )

    chat = client
    if chat is None:
        key = openai_api_key()
        if key is None:
            return InvestigationResult(
                question=q, status="missing_api_key", summary=MISSING_KEY_TEXT, seed_entity=seed
            )
        chat = OpenAIChatClient(api_key=key, model=openai_model())

    bundle, steps = run_skeleton(store, seed, q)
    budget = agentic_max_tool_calls() if max_tool_calls is None else max_tool_calls
    adaptive_used = 0

    while adaptive_used < budget:
        user = (
            f"Question: {q}\nBudget remaining: {budget - adaptive_used}\n\n"
            f"Evidence so far:\n{_evidence_payload(bundle, seed, q)}"
        )
        try:
            raw = chat.complete(system=PLANNER_SYSTEM, user=user)
            plan = _parse_json(raw)
        except (json.JSONDecodeError, KeyError, OSError, ValueError):
            break

        if plan.get("done") or not plan.get("tool"):
            steps.append(
                InvestigationStep(
                    phase="adaptive",
                    tool="planner",
                    args_summary="done",
                    result_summary="no further tools",
                )
            )
            break

        tool_name = str(plan.get("tool"))
        args = plan.get("args") if isinstance(plan.get("args"), dict) else {}
        if tool_name not in TOOL_NAMES:
            steps.append(
                InvestigationStep(
                    phase="adaptive",
                    tool=tool_name,
                    args_summary=str(args)[:80],
                    result_summary="rejected: not allowlisted",
                )
            )
            adaptive_used += 1
            continue

        try:
            result_summary = run_tool(store, bundle, tool_name, args, seed=seed)
        except (TypeError, ValueError) as exc:
            result_summary = f"error: {exc}"

        steps.append(
            InvestigationStep(
                phase="adaptive",
                tool=tool_name,
                args_summary=str(args)[:120],
                result_summary=result_summary,
            )
        )
        adaptive_used += 1

    # Report synthesis
    try:
        raw_report = chat.complete(
            system=REPORT_SYSTEM,
            user=f"Write the report.\n\n{_evidence_payload(bundle, seed, q)}",
        )
        parsed = _parse_json(raw_report)
    except (json.JSONDecodeError, KeyError, OSError, ValueError):
        return InvestigationResult(
            question=q,
            status="insufficient_evidence",
            summary=INSUFFICIENT_TEXT,
            seed_entity=seed,
            evidence=list(bundle.edges),
            doc_evidence=list(bundle.docs),
            steps=steps,
        )

    steps.append(
        InvestigationStep(
            phase="report",
            tool="synthesize",
            args_summary="report",
            result_summary=str(parsed.get("status", "")),
        )
    )

    citations = _filter_citations(parsed.get("citations") or [], bundle)
    doc_citations = _filter_doc_citations(parsed.get("doc_citations") or [], bundle)
    status = parsed.get("status", "insufficient_evidence")
    summary = str(parsed.get("summary") or "").strip() or INSUFFICIENT_TEXT
    findings_raw = parsed.get("findings") or []
    findings = [str(f) for f in findings_raw if str(f).strip()] if isinstance(findings_raw, list) else []

    has_retrieval = bool(bundle.edges) or bool(bundle.docs)
    has_cites = bool(citations) or bool(doc_citations)
    if status == "answered" and has_retrieval and not has_cites:
        return InvestigationResult(
            question=q,
            status="insufficient_evidence",
            summary=INSUFFICIENT_TEXT,
            seed_entity=seed,
            evidence=[],
            doc_evidence=[],
            steps=steps,
        )
    if status != "answered":
        return InvestigationResult(
            question=q,
            status="insufficient_evidence",
            summary=summary,
            findings=findings,
            seed_entity=seed,
            evidence=citations,
            doc_evidence=doc_citations,
            steps=steps,
        )

    return InvestigationResult(
        question=q,
        status="answered",
        summary=summary,
        findings=findings,
        seed_entity=seed,
        evidence=citations,
        doc_evidence=doc_citations,
        steps=steps,
    )
