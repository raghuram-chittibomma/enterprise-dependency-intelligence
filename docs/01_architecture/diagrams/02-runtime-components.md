# 02 — Runtime components

Package-level map of the running application (`src/`).

```mermaid
flowchart TB
  subgraph web [Presentation]
    Templates[Jinja2 templates]
    Static[CSS / Cytoscape.js]
    HTMX[HTMX partials]
  end

  subgraph api [API]
    Routes[FastAPI routes]
  end

  subgraph domain [Domain services]
    Queries[graph/queries]
    NLQuery[nlquery]
    Investigate[investigate]
    Intel[intelligence]
    Retrieval[retrieval]
  end

  subgraph persist [Persistence adapters]
    Neo4jStore[Neo4j GraphStore]
    Fallback[NetworkX + SQLite fallback]
    VecStore[SQLite vectors]
  end

  subgraph offline [Offline / batch]
    Datagen[datagen]
    Ingest[ingestion]
    Quality[quality]
    Recon[reconcile dry-run]
  end

  Templates --> Routes
  Static --> Templates
  HTMX --> Routes
  Routes --> Queries
  Routes --> NLQuery
  Routes --> Investigate
  Routes --> Intel
  NLQuery --> Queries
  NLQuery --> Retrieval
  Investigate --> Queries
  Investigate --> Retrieval
  Intel --> Queries
  Queries --> Neo4jStore
  Queries --> Fallback
  Retrieval --> VecStore
  Datagen --> Ingest
  Ingest --> Neo4jStore
  Ingest --> Recon
  Ingest --> Quality
```

**Design rule:** explorer and closed Ask call the same `queries` templates that Investigate tools and Intelligence scoring reuse—one graph contract for every milestone.
