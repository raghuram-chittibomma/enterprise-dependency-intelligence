"""FR11/FR13 steps 4-5: render a `RetrievalResult` into a plain-sentence
answer plus its supporting evidence (FR12). This module is ADR-0004's
`AnswerGenerator` extension point -- `TemplateAnswerGenerator` is MVP1's
fully deterministic implementation (fixed string templates, no LLM); MVP2
can add a second `AnswerGenerator` that consumes the exact same
`RetrievalResult` for LLM-backed grounded generation without touching
`intent.py`, `resolution.py`, or `engine.py`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol

from src.graph.queries import DependencyPath, EntityRef
from src.nlquery.engine import RetrievalResult
from src.nlquery.intent import QuestionType

AnswerStatus = Literal["answered", "unsupported", "not_found", "ambiguous"]


@dataclass(frozen=True)
class EvidenceEdge:
    """One graph edge cited as evidence for an answer (FR12) -- ids are
    included alongside names so the UI can link straight to each entity's
    detail page.
    """

    source_id: str
    source_name: str
    rel_type: str
    target_id: str
    target_name: str


@dataclass(frozen=True)
class AnswerResult:
    question: str
    status: AnswerStatus
    question_type: QuestionType | None
    text: str
    resolved_entities: list[EntityRef]
    evidence: list[EvidenceEdge]


class AnswerGenerator(Protocol):
    def generate(self, retrieval: RetrievalResult) -> AnswerResult: ...


UNSUPPORTED_TEXT = (
    'I can only answer a fixed set of dependency questions right now. Try asking things like '
    '"What does Order Service depend on?" or "Who owns applications downstream from '
    'Customer API v1?"'
)


def _not_found_text(name: str) -> str:
    return f'I couldn\'t find an entity matching "{name}" in the graph.'


def _ambiguous_text(name: str) -> str:
    return (
        f'"{name}" matches more than one entity and I can\'t tell which one you mean -- '
        "try a more specific name."
    )


def _path_chain_text(path: DependencyPath) -> str:
    if not path.edges:
        return path.nodes[0].name
    parts = [path.nodes[0].name]
    for node, edge in zip(path.nodes[1:], path.edges, strict=True):
        parts.append(f"-[{edge.rel_type}]-> {node.name}")
    return " ".join(parts)


def _path_evidence(path: DependencyPath) -> list[EvidenceEdge]:
    node_by_id = {node.id: node for node in path.nodes}
    return [
        EvidenceEdge(
            source_id=edge.source_id,
            source_name=node_by_id[edge.source_id].name,
            rel_type=edge.rel_type,
            target_id=edge.target_id,
            target_name=node_by_id[edge.target_id].name,
        )
        for edge in path.edges
    ]


def _handle_depends_on(retrieval: RetrievalResult) -> tuple[str, list[EvidenceEdge]]:
    entity = retrieval.resolved["entity"]
    upstream = retrieval.direct_dependencies.upstream if retrieval.direct_dependencies else []
    if not upstream:
        return f"{entity.name} doesn't have any recorded dependencies.", []
    names = ", ".join(f"{edge.entity.name} ({edge.rel_type})" for edge in upstream)
    text = f"{entity.name} depends on: {names}."
    evidence = [
        EvidenceEdge(
            source_id=entity.id,
            source_name=entity.name,
            rel_type=edge.rel_type,
            target_id=edge.entity.id,
            target_name=edge.entity.name,
        )
        for edge in upstream
    ]
    return text, evidence


def _handle_consumers_of(retrieval: RetrievalResult) -> tuple[str, list[EvidenceEdge]]:
    entity = retrieval.resolved["entity"]
    downstream = retrieval.direct_dependencies.downstream if retrieval.direct_dependencies else []
    consumers = [edge for edge in downstream if edge.rel_type == "CONSUMES"]
    if not consumers:
        return f"No applications or services directly consume {entity.name}.", []
    names = ", ".join(edge.entity.name for edge in consumers)
    text = f"The following directly consume {entity.name}: {names}."
    evidence = [
        EvidenceEdge(
            source_id=edge.entity.id,
            source_name=edge.entity.name,
            rel_type="CONSUMES",
            target_id=entity.id,
            target_name=entity.name,
        )
        for edge in consumers
    ]
    return text, evidence


def _handle_consumed_by(retrieval: RetrievalResult) -> tuple[str, list[EvidenceEdge]]:
    entity = retrieval.resolved["entity"]
    upstream = retrieval.direct_dependencies.upstream if retrieval.direct_dependencies else []
    apis = [edge for edge in upstream if edge.rel_type == "CONSUMES" and edge.entity.label == "API"]
    if not apis:
        return f"{entity.name} doesn't consume any APIs.", []
    names = ", ".join(edge.entity.name for edge in apis)
    text = f"{entity.name} consumes the following APIs: {names}."
    evidence = [
        EvidenceEdge(
            source_id=entity.id,
            source_name=entity.name,
            rel_type="CONSUMES",
            target_id=edge.entity.id,
            target_name=edge.entity.name,
        )
        for edge in apis
    ]
    return text, evidence


def _handle_used_by(retrieval: RetrievalResult) -> tuple[str, list[EvidenceEdge]]:
    entity = retrieval.resolved["entity"]
    downstream = retrieval.direct_dependencies.downstream if retrieval.direct_dependencies else []
    apps = [edge for edge in downstream if edge.entity.label == "Application"]
    if not apps:
        return f"No applications use {entity.name}.", []
    names = ", ".join(edge.entity.name for edge in apps)
    text = f"{entity.name} is used by: {names}."
    evidence = [
        EvidenceEdge(
            source_id=edge.entity.id,
            source_name=edge.entity.name,
            rel_type=edge.rel_type,
            target_id=entity.id,
            target_name=entity.name,
        )
        for edge in apps
    ]
    return text, evidence


def _handle_owners_downstream(retrieval: RetrievalResult) -> tuple[str, list[EvidenceEdge]]:
    entity = retrieval.resolved["entity"]
    groups = retrieval.ownership_rollup.groups if retrieval.ownership_rollup else []
    type_filter = retrieval.type_filter

    filtered: list[tuple[str | None, str, list[EntityRef]]] = []
    for group in groups:
        # Exclude the root itself -- "downstream from X" is about what
        # depends on X, not X's own ownership.
        entities = [e for e in group.entities if e.id != entity.id]
        if type_filter:
            entities = [e for e in entities if e.label == type_filter]
        if entities:
            team_id = group.team.id if group.team else None
            team_name = group.team.name if group.team else "Unowned"
            filtered.append((team_id, team_name, entities))

    if not filtered:
        noun = f"{type_filter.lower()}s" if type_filter else "entities"
        return f"No {noun} downstream from {entity.name} have a recorded owning team.", []

    parts = []
    evidence = []
    for team_id, team_name, entities in filtered:
        names = ", ".join(e.name for e in entities)
        parts.append(f"{team_name} ({names})")
        if team_id is not None:
            evidence.extend(
                EvidenceEdge(
                    source_id=e.id,
                    source_name=e.name,
                    rel_type="OWNED_BY",
                    target_id=team_id,
                    target_name=team_name,
                )
                for e in entities
            )
    text = f"Teams owning entities downstream from {entity.name}: " + "; ".join(parts) + "."
    return text, evidence


def _handle_capabilities_of(retrieval: RetrievalResult) -> tuple[str, list[EvidenceEdge]]:
    entity = retrieval.resolved["entity"]
    groups = retrieval.capability_rollup.groups if retrieval.capability_rollup else []
    if not groups:
        return f"No business capabilities depend on {entity.name}.", []

    parts = []
    evidence = []
    for group in groups:
        names = ", ".join(e.name for e in group.entities)
        parts.append(f"{group.capability.name} (via {names})")
        evidence.extend(
            EvidenceEdge(
                source_id=e.id,
                source_name=e.name,
                rel_type="SUPPORTS",
                target_id=group.capability.id,
                target_name=group.capability.name,
            )
            for e in group.entities
        )
    text = f"Business capabilities depending on {entity.name}: " + "; ".join(parts) + "."
    return text, evidence


def _handle_path_between(retrieval: RetrievalResult) -> tuple[str, list[EvidenceEdge]]:
    source = retrieval.resolved["source"]
    target = retrieval.resolved["target"]
    result = retrieval.path_result
    if result is None or result.shortest is None:
        return f"There is no dependency path between {source.name} and {target.name}.", []

    shortest = result.shortest
    hop_word = "hop" if shortest.hops == 1 else "hops"
    text = (
        f"The shortest dependency path between {source.name} and {target.name} is: "
        f"{_path_chain_text(shortest)} ({shortest.hops} {hop_word})."
    )
    if result.alternates:
        alt_text = "; ".join(_path_chain_text(path) for path in result.alternates)
        text += f" Alternate path(s): {alt_text}."

    evidence = _path_evidence(shortest)
    for alternate in result.alternates:
        evidence.extend(_path_evidence(alternate))
    return text, evidence


_HANDLERS = {
    "depends_on": _handle_depends_on,
    "consumers_of": _handle_consumers_of,
    "consumed_by": _handle_consumed_by,
    "used_by": _handle_used_by,
    "owners_downstream": _handle_owners_downstream,
    "capabilities_of": _handle_capabilities_of,
    "path_between": _handle_path_between,
}


class TemplateAnswerGenerator:
    """MVP1's `AnswerGenerator`: fixed string templates, zero LLM calls,
    per ADR-0004.
    """

    def generate(self, retrieval: RetrievalResult) -> AnswerResult:
        if retrieval.status == "unsupported":
            return AnswerResult(retrieval.question, "unsupported", None, UNSUPPORTED_TEXT, [], [])
        if retrieval.status == "not_found":
            text = _not_found_text(retrieval.unresolved_name or "")
            return AnswerResult(
                retrieval.question, "not_found", retrieval.question_type, text, [], []
            )
        if retrieval.status == "ambiguous":
            text = _ambiguous_text(retrieval.unresolved_name or "")
            return AnswerResult(
                retrieval.question, "ambiguous", retrieval.question_type, text, [], []
            )

        assert retrieval.question_type is not None  # guaranteed by "ok" status
        handler = _HANDLERS[retrieval.question_type]
        text, evidence = handler(retrieval)
        resolved_entities = list(retrieval.resolved.values()) if retrieval.resolved else []
        return AnswerResult(
            retrieval.question,
            "answered",
            retrieval.question_type,
            text,
            resolved_entities,
            evidence,
        )


def render_answer(retrieval: RetrievalResult) -> AnswerResult:
    return TemplateAnswerGenerator().generate(retrieval)
