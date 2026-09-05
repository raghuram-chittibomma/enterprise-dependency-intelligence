"""MVP2 LLM-backed grounded answer generation (`ADR-0005`).

`LLMAnswerGenerator` consumes an open-ended `RetrievalResult` (subgraph
already retrieved — no Text2Cypher) and asks OpenAI to answer using only
those edges. Citations are filtered to the retrieved set (FR15); anything
else becomes `insufficient_evidence` (FR16).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Protocol

from src.nlquery.answering import AnswerResult, EvidenceEdge
from src.nlquery.config import openai_api_key, openai_model
from src.nlquery.engine import RetrievalResult, SubgraphEdge

INSUFFICIENT_EVIDENCE_TEXT = (
    "Insufficient evidence in the retrieved dependency subgraph to answer "
    "that question without guessing. Try naming a specific system, or use one "
    "of the supported template questions."
)

MISSING_API_KEY_TEXT = (
    "Graph RAG is enabled, but OPENAI_API_KEY is not set. Closed template "
    "questions still work; set the key to enable open-ended answers."
)

SYSTEM_PROMPT = """You answer enterprise dependency questions using ONLY the
provided graph subgraph. Rules:
1. Only assert relationships that appear in the subgraph edges list.
2. If the subgraph does not contain enough evidence, set status to
   "insufficient_evidence" and explain briefly.
3. Reply with a single JSON object (no markdown fences) of the form:
{"status":"answered"|"insufficient_evidence","text":"...","citations":[{"source_id":"...","target_id":"...","rel_type":"..."}]}
4. Every citation must match an edge in the subgraph exactly (source_id,
   target_id, rel_type). Prefer fewer, precise citations.
"""


class ChatClient(Protocol):
    def complete(self, *, system: str, user: str) -> str: ...


@dataclass
class OpenAIChatClient:
    """Thin OpenAI Chat Completions wrapper. Constructed only when a key exists."""

    api_key: str
    model: str

    def complete(self, *, system: str, user: str) -> str:
        # Lazy import so unit tests / MVP1 path never require the package
        # unless Graph RAG actually runs.
        from openai import OpenAI

        client = OpenAI(api_key=self.api_key)
        response = client.chat.completions.create(
            model=self.model,
            temperature=0,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        content = response.choices[0].message.content
        return content or ""


def _edge_key(source_id: str, target_id: str, rel_type: str) -> tuple[str, str, str]:
    return (source_id, target_id, rel_type)


def _serialize_subgraph(retrieval: RetrievalResult) -> str:
    nodes = retrieval.open_subgraph_nodes or []
    edges = retrieval.open_subgraph_edges or []
    payload = {
        "seed_entities": [
            {"id": e.id, "label": e.label, "name": e.name}
            for e in (retrieval.resolved or {}).values()
            if not str(e.id).startswith("unused")
        ],
        "nodes": [{"id": n.id, "label": n.label, "name": n.name} for n in nodes],
        "edges": [
            {
                "source_id": e.source_id,
                "source_name": e.source_name,
                "rel_type": e.rel_type,
                "target_id": e.target_id,
                "target_name": e.target_name,
                "source_system": e.source_system,
                "evidence_type": e.evidence_type,
            }
            for e in edges
        ],
    }
    # Deduplicate seeds that appear as both entity and seed_N.
    seen: set[str] = set()
    unique_seeds = []
    for item in payload["seed_entities"]:
        if item["id"] in seen:
            continue
        seen.add(item["id"])
        unique_seeds.append(item)
    payload["seed_entities"] = unique_seeds
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _parse_model_json(raw: str) -> dict:
    text = raw.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1)
    else:
        start, end = text.find("{"), text.rfind("}")
        if start >= 0 and end > start:
            text = text[start : end + 1]
    return json.loads(text)


def _evidence_from_citations(
    citations: list[dict], edge_by_key: dict[tuple[str, str, str], SubgraphEdge]
) -> list[EvidenceEdge]:
    evidence: list[EvidenceEdge] = []
    seen: set[tuple[str, str, str]] = set()
    for citation in citations:
        try:
            key = _edge_key(citation["source_id"], citation["target_id"], citation["rel_type"])
        except (KeyError, TypeError):
            continue
        edge = edge_by_key.get(key)
        if edge is None or key in seen:
            continue
        seen.add(key)
        evidence.append(
            EvidenceEdge(
                source_id=edge.source_id,
                source_name=edge.source_name,
                rel_type=edge.rel_type,
                target_id=edge.target_id,
                target_name=edge.target_name,
                source_system=edge.source_system,
                source_record_id=edge.source_record_id,
                evidence_type=edge.evidence_type,
            )
        )
    return evidence


class LLMAnswerGenerator:
    """OpenAI-backed AnswerGenerator for open-ended Graph RAG retrievals."""

    def __init__(self, client: ChatClient | None = None) -> None:
        self._client = client

    def _client_or_configured(self) -> ChatClient | None:
        if self._client is not None:
            return self._client
        key = openai_api_key()
        if key is None:
            return None
        return OpenAIChatClient(api_key=key, model=openai_model())

    def generate(self, retrieval: RetrievalResult) -> AnswerResult:
        if retrieval.status == "not_found":
            name = retrieval.unresolved_name or ""
            text = f'I couldn\'t find an entity matching "{name}" in the graph.'
            return AnswerResult(retrieval.question, "not_found", "open_ended", text, [], [])
        if retrieval.status == "ambiguous":
            name = retrieval.unresolved_name or ""
            text = (
                f'"{name}" matches more than one entity and I can\'t tell which '
                "one you mean -- try a more specific name."
            )
            return AnswerResult(retrieval.question, "ambiguous", "open_ended", text, [], [])
        if retrieval.status != "ok" or not retrieval.open_ended:
            return AnswerResult(
                retrieval.question,
                "unsupported",
                "open_ended",
                INSUFFICIENT_EVIDENCE_TEXT,
                [],
                [],
            )

        client = self._client_or_configured()
        if client is None:
            return AnswerResult(
                retrieval.question, "unsupported", "open_ended", MISSING_API_KEY_TEXT, [], []
            )

        edges = retrieval.open_subgraph_edges or []
        edge_by_key = {
            _edge_key(e.source_id, e.target_id, e.rel_type): e for e in edges
        }
        user_prompt = (
            f"Question: {retrieval.question}\n\nSubgraph JSON:\n{_serialize_subgraph(retrieval)}"
        )
        try:
            raw = client.complete(system=SYSTEM_PROMPT, user=user_prompt)
            parsed = _parse_model_json(raw)
        except (json.JSONDecodeError, KeyError, IndexError, OSError, ValueError):
            return AnswerResult(
                retrieval.question,
                "insufficient_evidence",
                "open_ended",
                INSUFFICIENT_EVIDENCE_TEXT,
                list((retrieval.resolved or {}).values())[:3],
                [],
            )

        status = parsed.get("status", "insufficient_evidence")
        text = str(parsed.get("text") or "").strip() or INSUFFICIENT_EVIDENCE_TEXT
        citations = parsed.get("citations") or []
        if not isinstance(citations, list):
            citations = []
        evidence = _evidence_from_citations(citations, edge_by_key)

        # Faithfulness gate (FR15/FR16): answered requires at least one valid
        # in-subgraph citation when the subgraph had edges; otherwise refuse.
        if status == "answered" and edges and not evidence:
            return AnswerResult(
                retrieval.question,
                "insufficient_evidence",
                "open_ended",
                INSUFFICIENT_EVIDENCE_TEXT,
                list({e.id: e for e in (retrieval.resolved or {}).values()}.values()),
                [],
            )
        if status != "answered":
            return AnswerResult(
                retrieval.question,
                "insufficient_evidence",
                "open_ended",
                text if text else INSUFFICIENT_EVIDENCE_TEXT,
                list({e.id: e for e in (retrieval.resolved or {}).values()}.values()),
                evidence,
            )

        resolved = list({e.id: e for e in (retrieval.resolved or {}).values()}.values())
        return AnswerResult(
            retrieval.question, "answered", "open_ended", text, resolved, evidence
        )
