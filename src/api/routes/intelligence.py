"""MVP5 Intelligence HTMX routes (`ADR-0008`)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from src.api.deps import get_store
from src.graph.queries import DEFAULT_TRAVERSAL_DEPTH, get_entity_detail
from src.graph.store import GraphStore
from src.intelligence.drift import detect_drift
from src.intelligence.narrative import narrate_risk, narrate_whatif
from src.intelligence.rationalization import rationalize_technologies
from src.intelligence.risk import compute_risk_score
from src.intelligence.team_rollup import (
    compute_team_owned_risk_rollup,
    simulate_team_portfolio_impact,
)
from src.intelligence.whatif import simulate_retirement

router = APIRouter()


@router.get("/intelligence", response_class=HTMLResponse)
async def intelligence_hub(request: Request) -> HTMLResponse:
    templates = request.app.state.templates
    return templates.TemplateResponse(
        request=request, name="pages/intelligence.html", context={}
    )


@router.get("/intelligence/drift", response_class=HTMLResponse)
async def intelligence_drift(
    request: Request, store: GraphStore = Depends(get_store)
) -> HTMLResponse:
    templates = request.app.state.templates
    signals = detect_drift(store)
    return templates.TemplateResponse(
        request=request,
        name="pages/intelligence_drift.html",
        context={"signals": signals},
    )


@router.get("/intelligence/rationalize", response_class=HTMLResponse)
async def intelligence_rationalize(
    request: Request, store: GraphStore = Depends(get_store)
) -> HTMLResponse:
    templates = request.app.state.templates
    report = rationalize_technologies(store)
    return templates.TemplateResponse(
        request=request,
        name="pages/intelligence_rationalize.html",
        context={"report": report},
    )


@router.get("/entities/{entity_id}/risk", response_class=HTMLResponse)
async def entity_risk_partial(
    request: Request,
    entity_id: str,
    store: GraphStore = Depends(get_store),
) -> HTMLResponse:
    templates = request.app.state.templates
    detail = get_entity_detail(store, entity_id)
    if detail is not None and detail.label == "Team":
        rollup = compute_team_owned_risk_rollup(store, entity_id)
        return templates.TemplateResponse(
            request=request,
            name="partials/team_risk_rollup.html",
            context={"rollup": rollup, "entity_id": entity_id},
        )
    assessment = compute_risk_score(store, entity_id)
    if assessment is not None:
        assessment = narrate_risk(assessment)
    return templates.TemplateResponse(
        request=request,
        name="partials/risk_panel.html",
        context={"assessment": assessment, "entity_id": entity_id},
    )


@router.get("/entities/{entity_id}/what-if", response_class=HTMLResponse)
async def entity_whatif_partial(
    request: Request,
    entity_id: str,
    depth: int = DEFAULT_TRAVERSAL_DEPTH,
    store: GraphStore = Depends(get_store),
) -> HTMLResponse:
    templates = request.app.state.templates
    detail = get_entity_detail(store, entity_id)
    if detail is None:
        return templates.TemplateResponse(
            request=request,
            name="partials/whatif_panel.html",
            context={"result": None, "entity_id": entity_id, "depth": depth},
        )
    if detail.label == "Team":
        portfolio = simulate_team_portfolio_impact(
            store, entity_id, max_depth=depth
        )
        return templates.TemplateResponse(
            request=request,
            name="partials/team_whatif_panel.html",
            context={"portfolio": portfolio, "entity_id": entity_id, "depth": depth},
        )
    result = simulate_retirement(store, entity_id, max_depth=depth)
    if result is not None:
        result = narrate_whatif(result)
    return templates.TemplateResponse(
        request=request,
        name="partials/whatif_panel.html",
        context={"result": result, "entity_id": entity_id, "depth": depth},
    )
