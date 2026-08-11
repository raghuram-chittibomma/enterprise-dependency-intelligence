"""Full HTML document routes (as opposed to the HTMX partials in the other
route modules, which render fragments swapped into one of these pages).
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    templates = request.app.state.templates
    return templates.TemplateResponse(request=request, name="pages/search.html", context={})
