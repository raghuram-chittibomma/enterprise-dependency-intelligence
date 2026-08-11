"""FR1: entity search. An HTMX partial route -- the search page's input box
(`src/web/templates/pages/search.html`) calls this on every keystroke
(debounced client-side) and swaps the response into the results container.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from src.api.deps import get_store
from src.graph.queries import search_entities
from src.graph.store import GraphStore

router = APIRouter()


@router.get("/search", response_class=HTMLResponse)
async def search_route(
    request: Request, q: str = "", store: GraphStore = Depends(get_store)
) -> HTMLResponse:
    templates = request.app.state.templates
    results = search_entities(store, q) if q.strip() else []
    return templates.TemplateResponse(
        request=request,
        name="partials/search_results.html",
        context={"results": results, "query": q},
    )
