"""The `graph_store` extension point (ADR-0001): a backend-agnostic interface
over the graph database, with a Neo4j implementation (primary) and a
NetworkX+SQLite implementation (fallback, for when the remote Docker host is
unreachable). See `docs/01_architecture/ARCHITECTURE.md`.
"""

from src.graph.config import get_graph_store
from src.graph.store import GraphStore
from src.graph.types import HealthCheckResult

__all__ = ["GraphStore", "HealthCheckResult", "get_graph_store"]
