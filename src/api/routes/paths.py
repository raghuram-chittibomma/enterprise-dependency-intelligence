"""FR6/FR7: the dependency path explorer -- given two entities, the
shortest dependency path between them plus any distinct alternates. A
two-step HTMX flow hung off the entity detail page: search for the
"other" entity, then render the computed path(s) once one is picked.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from src.api.deps import get_store
from src.graph.queries import get_dependency_paths, get_entity_detail, search_entities
from src.graph.store import GraphStore

router = APIRouter()


@router.get("/entities/{entity_id}/paths/search", response_class=HTMLResponse)
async def paths_search(
    request: Request, entity_id: str, q: str = "", store: GraphStore = Depends(get_store)
) -> HTMLResponse:
    templates = request.app.state.templates
    results = [r for r in search_entities(store, q) if r.id != entity_id] if q.strip() else []
    return templates.TemplateResponse(
        request=request,
        name="partials/path_target_results.html",
        context={"results": results, "query": q, "source_id": entity_id},
    )


@router.get("/entities/{entity_id}/paths/result", response_class=HTMLResponse)
async def paths_result(
    request: Request, entity_id: str, target: str, store: GraphStore = Depends(get_store)
) -> HTMLResponse:
    templates = request.app.state.templates
    result = get_dependency_paths(store, entity_id, target)
    target_detail = get_entity_detail(store, target)
    return templates.TemplateResponse(
        request=request,
        name="partials/path_result.html",
        context={"result": result, "target_name": target_detail.name if target_detail else target},
    )
