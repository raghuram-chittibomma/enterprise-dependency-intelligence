"""Public entry point for the NL query layer: classify → resolve → retrieve
→ answer → log. Routes and tests call `ask()`; everything else in this
package is an implementation detail of that one call.
"""

from __future__ import annotations

from src.graph.store import GraphStore
from src.nlquery.answering import AnswerResult, render_answer
from src.nlquery.engine import retrieve
from src.nlquery.logging import log_answer, timed


def ask(store: GraphStore, question: str) -> AnswerResult:
    """Answer `question` against `store`. Always returns an `AnswerResult`
    -- including for FR13 non-answers -- never raises for an unsupported
    or unresolvable question.
    """
    def _run() -> AnswerResult:
        return render_answer(retrieve(store, question))

    answer, latency_ms = timed(_run)
    log_answer(answer, latency_ms)
    return answer
