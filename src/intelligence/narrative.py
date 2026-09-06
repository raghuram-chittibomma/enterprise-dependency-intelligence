"""Optional LLM narrative over computed intelligence factors (`ADR-0008`, FR27)."""

from __future__ import annotations

import json
import re
from typing import Protocol

from src.intelligence.config import (
    intelligence_narrative_enabled,
    openai_api_key,
    openai_model,
)
from src.intelligence.models import RiskAssessment
from src.intelligence.whatif import WhatIfResult
from src.nlquery.llm import OpenAIChatClient

NARRATIVE_SYSTEM = """You explain Meridian Retail Group dependency intelligence results.
Use ONLY the provided JSON. Reply JSON only:
{"status":"ok"|"refuse","text":"...","cited_factor_ids":["..."]}
Every cited_factor_id must appear in the payload factors list.
Never invent or change numeric scores. If factors are empty, status=refuse.
"""


class ChatClient(Protocol):
    def complete(self, *, system: str, user: str) -> str: ...


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


def _gate(text: str, allowed: set[str], cited: list) -> str | None:
    cited_ids = {str(c) for c in (cited or [])}
    if not cited_ids.issubset(allowed):
        return None
    cleaned = (text or "").strip()
    return cleaned or None


def narrate_risk(
    assessment: RiskAssessment,
    *,
    client: ChatClient | None = None,
) -> RiskAssessment:
    """Attach a narrative when enabled; otherwise return assessment unchanged."""
    if client is None and not intelligence_narrative_enabled():
        return assessment
    chat = client
    if chat is None:
        key = openai_api_key()
        if key is None:
            return assessment
        chat = OpenAIChatClient(api_key=key, model=openai_model())

    allowed = {f.id for f in assessment.factors}
    payload = {
        "entity": assessment.entity_name,
        "score": assessment.score,
        "band": assessment.band,
        "factors": [
            {"id": f.id, "label": f.label, "points": f.points} for f in assessment.factors
        ],
    }
    try:
        raw = chat.complete(
            system=NARRATIVE_SYSTEM,
            user=json.dumps(payload, ensure_ascii=False),
        )
        data = _parse_json(raw)
    except (json.JSONDecodeError, TypeError, ValueError):
        return assessment
    if data.get("status") != "ok":
        return assessment
    text = _gate(str(data.get("text") or ""), allowed, data.get("cited_factor_ids") or [])
    if text is None:
        return assessment
    return RiskAssessment(
        entity_id=assessment.entity_id,
        entity_name=assessment.entity_name,
        entity_label=assessment.entity_label,
        score=assessment.score,
        band=assessment.band,
        factors=assessment.factors,
        narrative=text,
    )


def narrate_whatif(
    result: WhatIfResult,
    *,
    client: ChatClient | None = None,
) -> WhatIfResult:
    if client is None and not intelligence_narrative_enabled():
        return result
    chat = client
    if chat is None:
        key = openai_api_key()
        if key is None:
            return result
        chat = OpenAIChatClient(api_key=key, model=openai_model())

    # Synthetic factor ids for what-if narrative gating.
    factors = [
        {
            "id": "blast",
            "label": f"{len(result.downstream)} downstream entities",
            "points": len(result.downstream),
        },
        {
            "id": "stakeholders",
            "label": f"{len(result.stakeholder_teams)} teams",
            "points": len(result.stakeholder_teams),
        },
        {
            "id": "capabilities",
            "label": f"{len(result.capabilities)} capabilities",
            "points": len(result.capabilities),
        },
    ]
    allowed = {f["id"] for f in factors}
    payload = {
        "scenario": result.scenario,
        "seed": result.seed.name,
        "factors": factors,
        "top_impacted": [
            {"name": a.entity_name, "score": a.score, "band": a.band}
            for a in result.top_impacted
        ],
    }
    try:
        raw = chat.complete(
            system=NARRATIVE_SYSTEM,
            user=json.dumps(payload, ensure_ascii=False),
        )
        data = _parse_json(raw)
    except (json.JSONDecodeError, TypeError, ValueError):
        return result
    if data.get("status") != "ok":
        return result
    text = _gate(str(data.get("text") or ""), allowed, data.get("cited_factor_ids") or [])
    if text is None:
        return result
    return WhatIfResult(
        seed=result.seed,
        scenario=result.scenario,
        max_depth=result.max_depth,
        downstream=result.downstream,
        upstream_critical=result.upstream_critical,
        stakeholder_teams=result.stakeholder_teams,
        unowned_entities=result.unowned_entities,
        capabilities=result.capabilities,
        top_impacted=result.top_impacted,
        narrative=text,
    )
