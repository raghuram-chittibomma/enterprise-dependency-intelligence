"""FastAPI application factory (`ARCHITECTURE.md`'s "App" layer). Wires up
the graph store (one instance for the process lifetime -- MVP1 is
single-process/local-first per `PROJECT_CHARTER.md`'s constraints), Jinja2
templates, static files, and every route module. Run via
`uvicorn src.api.main:app --reload` (see `docs/03_operations/RUNBOOK.md`).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from src.api.routes import ask, entities, investigate, pages, paths, search
from src.env_loader import load_project_env
from src.graph.config import get_graph_store

load_project_env()

WEB_DIR = Path(__file__).resolve().parent.parent / "web"
templates = Jinja2Templates(directory=str(WEB_DIR / "templates"))


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.store = get_graph_store()
    try:
        yield
    finally:
        app.state.store.close()


def create_app() -> FastAPI:
    app = FastAPI(title="Enterprise Dependency Intelligence", lifespan=lifespan)
    app.state.templates = templates
    app.mount("/static", StaticFiles(directory=str(WEB_DIR / "static")), name="static")
    app.include_router(pages.router)
    app.include_router(search.router)
    app.include_router(entities.router)
    app.include_router(paths.router)
    app.include_router(ask.router)
    app.include_router(investigate.router)
    return app


app = create_app()
