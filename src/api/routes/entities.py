"""FR2 (metadata) + FR3 (direct dependencies) + FR4/FR5 (bounded upstream/
downstream traversal): the entity detail page -- the destination search
results (FR1) link to.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse

from src.api.deps import get_store
from src.graph.queries import (
    DEFAULT_TRAVERSAL_DEPTH,
    TraversalDirection,
    get_dependency_traversal,
    get_direct_dependencies,
    get_entity_detail,
)
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
    dependencies = get_direct_dependencies(store, entity_id)
    return templates.TemplateResponse(
        request=request,
        name="pages/entity_detail.html",
        context={"entity": detail, "dependencies": dependencies},
    )


@router.get("/entities/{entity_id}/graph")
async def entity_graph(
    entity_id: str,
    direction: TraversalDirection = "upstream",
    depth: int = DEFAULT_TRAVERSAL_DEPTH,
    store: GraphStore = Depends(get_store),
) -> JSONResponse:
    """FR4/FR5 subgraph data, in a viz-library-agnostic shape (plain node/
    edge lists) so `graph.js` can adapt it to Cytoscape.js without this
    route knowing anything about the rendering library.
    """
    result = get_dependency_traversal(store, entity_id, direction, max_depth=depth)
    if result is None:
        raise HTTPException(status_code=404, detail=f"No entity with id {entity_id!r}")
    return JSONResponse(
        {
            "root_id": result.root_id,
            "direction": result.direction,
            "max_depth": result.max_depth,
            "nodes": [
                {
                    "id": node.entity.id,
                    "label": node.entity.label,
                    "name": node.entity.name,
                    "criticality": node.entity.criticality,
                    "lifecycle_status": node.entity.lifecycle_status,
                    "depth": node.depth,
                }
                for node in result.nodes
            ],
            "edges": [
                {
                    "source_id": edge.source_id,
                    "target_id": edge.target_id,
                    "rel_type": edge.rel_type,
                }
                for edge in result.edges
            ],
        }
    )
