"""FR2: entity detail page -- the destination search results (FR1) link to.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from src.api.deps import get_store
from src.graph.queries import get_entity_detail
from src.graph.store import GraphStore

router = APIRouter()


@router.get("/entities/{entity_id}", response_class=HTMLResponse)
async def entity_detail(
    request: Request, entity_id: str, store: GraphStore = Depends(get_store)
) -> HTMLResponse:
    templates = request.app.state.templates
    detail = get_entity_detail(store, entity_id)
    if detail is None:
        return templates.TemplateResponse(
            request=request,
            name="pages/entity_not_found.html",
            context={"entity_id": entity_id},
            status_code=404,
        )
    return templates.TemplateResponse(
        request=request, name="pages/entity_detail.html", context={"entity": detail}
    )
