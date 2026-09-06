"""Public Investigate entry point (`ADR-0007`)."""

from __future__ import annotations

from src.graph.store import GraphStore
from src.investigate.agent import DISABLED_TEXT, ChatClient, run_investigation
from src.investigate.config import agentic_investigation_enabled
from src.investigate.models import InvestigationResult


def investigate(
    store: GraphStore,
    question: str,
    *,
    client: ChatClient | None = None,
    max_tool_calls: int | None = None,
) -> InvestigationResult:
    if not agentic_investigation_enabled() and client is None:
        # Tests may inject a client while the flag is off; production path
        # respects the flag unless a client is explicitly provided.
        return InvestigationResult(
            question=question, status="disabled", summary=DISABLED_TEXT
        )
    return run_investigation(
        store, question, client=client, max_tool_calls=max_tool_calls
    )


__all__ = ["investigate", "InvestigationResult"]
