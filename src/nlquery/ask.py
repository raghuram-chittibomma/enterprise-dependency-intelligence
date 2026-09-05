"""Public entry point for the NL query layer: classify → resolve → retrieve
→ answer → log. Routes and tests call `ask()`; everything else in this
package is an implementation detail of that one call.

MVP2 (`ADR-0005`): closed templates stay deterministic; unmatched questions
optionally go through open-ended subgraph retrieval + LLMAnswerGenerator
when `GRAPH_RAG_ENABLED` is set.

MVP3 (`ADR-0006`): when `HYBRID_DOC_RAG_ENABLED` is also set, open-ended
retrieval fuses top-k document chunks with the subgraph.
"""

from __future__ import annotations

from src.graph.store import GraphStore
from src.nlquery.answering import AnswerResult, render_answer
from src.nlquery.config import graph_rag_enabled, hybrid_doc_rag_enabled
from src.nlquery.engine import retrieve
from src.nlquery.graphrag import retrieve_open_ended
from src.nlquery.llm import LLMAnswerGenerator
from src.nlquery.logging import log_answer, timed


def ask(store: GraphStore, question: str) -> AnswerResult:
    """Answer `question` against `store`. Always returns an `AnswerResult`
    -- including for FR13/FR16 non-answers -- never raises for an
    unsupported or unresolvable question.
    """

    def _run() -> AnswerResult:
        closed = retrieve(store, question)
        if closed.status != "unsupported":
            return render_answer(closed)
        if not graph_rag_enabled():
            return render_answer(closed)
        open_retrieval = retrieve_open_ended(
            store, question, include_docs=hybrid_doc_rag_enabled()
        )
        return LLMAnswerGenerator().generate(open_retrieval)

    answer, latency_ms = timed(_run)
    log_answer(answer, latency_ms)
    return answer
