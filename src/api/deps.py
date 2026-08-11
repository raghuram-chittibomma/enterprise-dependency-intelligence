"""Shared FastAPI dependencies. Currently just the one graph-store seam --
routes depend on `get_store`, never construct a store themselves, so tests
can swap in a pre-seeded fixture store via `app.dependency_overrides`
instead of hitting the real configured backend.
"""

from __future__ import annotations

from fastapi import Request

from src.graph.store import GraphStore


def get_store(request: Request) -> GraphStore:
    return request.app.state.store
