"""MVP4 Investigate HTMX route (`ADR-0007`)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse

from src.api.deps import get_store
from src.graph.store import GraphStore
from src.investigate.config import agentic_investigation_enabled
from src.investigate.run import investigate

router = APIRouter()


@router.post("/investigate", response_class=HTMLResponse)
async def investigate_route(
    request: Request,
    q: str = Form(""),
    store: GraphStore = Depends(get_store),
) -> HTMLResponse:
    templates = request.app.state.templates
    result = None
    if q.strip():
        if not agentic_investigation_enabled():
            from src.investigate.models import InvestigationResult
            from src.investigate.agent import DISABLED_TEXT

            result = InvestigationResult(question=q, status="disabled", summary=DISABLED_TEXT)
        else:
            result = investigate(store, q)
    return templates.TemplateResponse(
        request=request,
        name="partials/investigate_report.html",
        context={"result": result, "query": q},
    )
