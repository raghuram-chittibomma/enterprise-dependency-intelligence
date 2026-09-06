"""Reads graph store configuration from the environment and builds the
right `GraphStore` implementation (ADR-0001). No config file needed for
MVP1's single local backend.
"""

from __future__ import annotations

import os

from src.env_loader import load_project_env
from src.graph.store import GraphStore

load_project_env()

DEFAULT_NEO4J_URI = "bolt://localhost:7687"
DEFAULT_NEO4J_USER = "neo4j"
DEFAULT_NEO4J_PASSWORD = "edi-local-dev"
DEFAULT_FALLBACK_SQLITE_PATH = "data/graph_fallback.sqlite3"


def get_graph_store() -> GraphStore:
    backend = os.environ.get("GRAPH_STORE_BACKEND", "neo4j").lower()

    if backend == "fallback":
        from src.graph.fallback_store import FallbackGraphStore

        sqlite_path = os.environ.get("GRAPH_FALLBACK_SQLITE_PATH", DEFAULT_FALLBACK_SQLITE_PATH)
        return FallbackGraphStore(sqlite_path=sqlite_path)

    if backend == "neo4j":
        from src.graph.neo4j_store import Neo4jGraphStore

        uri = os.environ.get("NEO4J_URI", DEFAULT_NEO4J_URI)
        user = os.environ.get("NEO4J_USER", DEFAULT_NEO4J_USER)
        password = os.environ.get("NEO4J_PASSWORD", DEFAULT_NEO4J_PASSWORD)
        return Neo4jGraphStore(uri, user, password)

    raise ValueError(f"Unknown GRAPH_STORE_BACKEND {backend!r}; expected 'neo4j' or 'fallback'")
