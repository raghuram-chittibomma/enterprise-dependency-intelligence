"""Structured JSON observability for the NL query layer
(`PRODUCT_BRIEF.md`'s Observability constraint: one JSON log line per
question with question text, resolved intent, matched entities, and
latency -- written locally, no dashboard in MVP1).
"""

from __future__ import annotations

import json
import os
import time
from collections.abc import Callable
from pathlib import Path
from typing import TypeVar

from src.nlquery.answering import AnswerResult

DEFAULT_NLQUERY_LOG_PATH = "data/nlquery.log"

T = TypeVar("T")


def _log_path() -> Path:
    return Path(os.environ.get("NLQUERY_LOG_PATH", DEFAULT_NLQUERY_LOG_PATH))


def log_answer(answer: AnswerResult, latency_ms: float) -> None:
    """Append one JSON line for `answer`. Failures here must never break
    the ask path itself -- observability is best-effort for MVP1.
    """
    record = {
        "question": answer.question,
        "status": answer.status,
        "question_type": answer.question_type,
        "matched_entities": [
            {"id": entity.id, "label": entity.label, "name": entity.name}
            for entity in answer.resolved_entities
        ],
        "latency_ms": round(latency_ms, 2),
    }
    try:
        path = _log_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError:
        # Local-file observability is best-effort -- a full disk or a
        # permissions issue must not turn a successful answer into a 500.
        pass


def timed(fn: Callable[[], T]) -> tuple[T, float]:
    """Run `fn` and return `(result, elapsed_ms)`."""
    started = time.perf_counter()
    result = fn()
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    return result, elapsed_ms
