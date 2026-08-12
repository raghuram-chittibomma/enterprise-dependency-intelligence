"""FR11/FR13 step 1: intent classification against the 7 fixed question
shapes (`docs/00_project/PRODUCT_BRIEF.md`'s closed template set) --
keyword/regex matching only, per ADR-0004. `classify()` returns `None`
for anything outside the 7 shapes, which the engine turns into FR13's
explicit "not supported" response.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

QuestionType = Literal[
    "consumers_of",
    "depends_on",
    "owners_downstream",
    "capabilities_of",
    "path_between",
    "consumed_by",
    "used_by",
]

# Plural type-words the "owners downstream" question (Q3) may name, mapped
# to the node label to filter the rollup by. An unrecognized word means
# "don't filter" rather than "no match" -- the question shape still holds.
LABEL_BY_TYPE_WORD = {
    "application": "Application",
    "applications": "Application",
    "service": "Service",
    "services": "Service",
    "api": "API",
    "apis": "API",
    "database": "Database",
    "databases": "Database",
    "pipeline": "DataPipeline",
    "pipelines": "DataPipeline",
    "report": "Report",
    "reports": "Report",
    "team": "Team",
    "teams": "Team",
}


@dataclass(frozen=True)
class ParsedIntent:
    question_type: QuestionType
    entities: dict[str, str]


def _strip(text: str) -> str:
    return text.strip().rstrip("?").strip()


# Checked in this order: the more distinctive/specific shapes first, so a
# question that could technically match two patterns (e.g. both Q4's and
# Q2's "depend on") resolves to the more specific one.
_PATTERNS: list[tuple[QuestionType, re.Pattern[str]]] = [
    (
        "path_between",
        re.compile(r"(?:dependency\s+)?path\s+between\s+(?P<source>.+?)\s+and\s+(?P<target>.+)$"),
    ),
    (
        "owners_downstream",
        re.compile(
            r"who\s+owns?\s+(?P<entity_type>\w+)\s+downstream\s+(?:from|of)\s+(?P<entity>.+)$"
        ),
    ),
    (
        "capabilities_of",
        re.compile(
            r"(?:which|what)\s+business\s+capabilit\w*\s+depend\w*\s+on\s+(?P<entity>.+)$"
        ),
    ),
    (
        "consumed_by",
        re.compile(r"(?:which|what)\s+apis?\s+.*?consumed\s+by\s+(?P<entity>.+)$"),
    ),
    (
        "consumers_of",
        re.compile(
            r"what\s+(?:applications?|services?)(?:\s*/\s*|\s+and\s+)?"
            r"(?:applications?|services?)?\s+(?:directly\s+)?consumes?\s+(?P<entity>.+)$"
        ),
    ),
    (
        "used_by",
        re.compile(r"what\s+applications?\s+use\s+(?P<entity>.+)$"),
    ),
    (
        "depends_on",
        re.compile(r"what\s+does\s+(?P<entity>.+?)\s+depend\s+on$"),
    ),
]


def classify(question: str) -> ParsedIntent | None:
    """Match `question` against the 7 fixed shapes, case-insensitively and
    tolerant of a trailing "?". Returns `None` if nothing matches.
    """
    normalized = _strip(question)
    for question_type, pattern in _PATTERNS:
        match = pattern.search(normalized.lower())
        if match is None:
            continue
        # Slice the *original*-case string at the matched span so extracted
        # entity names keep their real casing for resolution/display.
        groups = {
            name: normalized[match.start(name) : match.end(name)].strip()
            for name in match.groupdict()
        }
        if any(not value for value in groups.values()):
            continue
        return ParsedIntent(question_type=question_type, entities=groups)
    return None
