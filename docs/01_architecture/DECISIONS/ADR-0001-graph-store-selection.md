# ADR-0001: Graph store selection for MVP1

Status: Accepted

## Context

The application's core value is dependency traversal and path-finding over a property graph. This needs a store with native multi-hop traversal and a query language expressive enough for variable-depth traversal and shortest/alternate path queries (FR3–FR7), while staying local-first and free to run.

Three options were considered:

1. **Neo4j Community Edition**, self-hosted via Docker. Industry-standard property graph database with Cypher, native shortest-path functions, and a mature Python driver. Free (Community Edition), self-hostable, and has first-party Graph RAG tooling (`neo4j-graphrag-python` — Text2Cypher, VectorCypherRetriever) that directly matches the MVP2 roadmap.
2. **Kuzu / LadybugDB**, an embedded graph database requiring no server process. Kuzu was archived after Apple's acquisition of the team (October 2025); a community fork, LadybugDB, keeps it alive but with materially less certainty about long-term maintenance.
3. **NetworkX + SQLite**: an in-process graph library (NetworkX) for traversal, backed by SQLite for persistence of node/relationship properties. Zero external infrastructure, but no native query language — traversal logic would be hand-written Python, and it would need to be re-proven at each future scale increase.

The dev machine does not run Docker directly; a Docker daemon is available on a separate Windows host on the local LAN (`192.168.4.52`), reachable over `DOCKER_HOST=tcp://192.168.4.52:2375` once the daemon's TCP endpoint and firewall are opened (see `docs/03_operations/RUNBOOK.md`).

## Decision

Use **Neo4j Community Edition**, run as a Docker container on the remote LAN Docker host, as the MVP1 graph store, accessed via the official `neo4j` Python driver over Bolt. If that Docker host becomes unreachable during development, fall back to **NetworkX + SQLite** behind the same `GraphStore` extension point (`src/graph/store.py`) rather than blocking work on infrastructure — the fallback only needs to support the same query surface (search, detail, traversal, path-finding, ownership rollup, capability view), not full Cypher parity.

## Consequences

- **Easier**: Cypher gives native, well-tested traversal and shortest-path operators (`shortestPath`, variable-length patterns) instead of hand-rolled graph algorithms — directly de-risks FR4–FR7. MVP2's Graph RAG work can build on `neo4j-graphrag-python` with no store migration.
- **Easier**: Neo4j Community Edition and Docker are both free; no licensing decision needed.
- **Harder**: introduces a network dependency on a separate physical machine for local development, which the NetworkX+SQLite fallback exists specifically to mitigate. The fallback is a documented degraded mode, not a silently-diverging second implementation — MVP1 acceptance is defined against Neo4j; the fallback is a continuity measure only.
- **Rejected: Kuzu/LadybugDB** — embedded (no server dependency) was attractive, but the Kuzu project's archival and LadybugDB's unproven maintenance trajectory made it too risky as the primary store for a multi-month roadmap that depends on it working.
- **Rejected: NetworkX + SQLite as primary** — avoids all infrastructure, but hand-written traversal algorithms are more code to get right and re-verify than a mature query language, for no benefit once Docker connectivity was confirmed reachable.
