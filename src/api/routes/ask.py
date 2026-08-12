"""FR11/FR13: the natural-language question box. An HTMX partial route --
the search page's ask form (`src/web/templates/pages/search.html`) posts
here and swaps the response into the answer container.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse

from src.api.deps import get_store
from src.graph.store import GraphStore
from src.nlquery.ask import ask

router = APIRouter()


@router.post("/ask", response_class=HTMLResponse)
async def ask_route(
    request: Request,
    q: str = Form(""),
    store: GraphStore = Depends(get_store),
) -> HTMLResponse:
    templates = request.app.state.templates
    answer = ask(store, q) if q.strip() else None
    return templates.TemplateResponse(
        request=request,
        name="partials/ask_answer.html",
        context={"answer": answer, "query": q},
    )
