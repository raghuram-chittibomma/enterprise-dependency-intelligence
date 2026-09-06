# Runbook

Status: draft (will be updated as increments land — Docker/Neo4j section is accepted; app run commands fill in as `src/` is built)

Read by: `readme-runbook-documentation` skill.

## Local development

### Prerequisites

- Python 3.11+ with a virtualenv at `.venv/`.
- Docker Engine + Compose (Docker Desktop, or equivalent) so Neo4j can run locally.
- Optional: willingness to use the embedded NetworkX+SQLite store (`GRAPH_STORE_BACKEND=fallback`) if Docker/Neo4j is unavailable — see `ADR-0001-graph-store-selection.md`.

### Graph store (localhost)

From the repo root:

```bash
docker compose up -d neo4j
# Neo4j Browser: http://localhost:7474  |  Bolt: bolt://localhost:7687
# Default local-dev credentials (synthetic data only): neo4j / edi-local-dev
# Override via NEO4J_PASSWORD in the shell or `.env`

python -m src.graph.healthcheck    # verifies connectivity and bootstraps schema constraints
```

If Compose is installed as a standalone binary on your machine, use `docker-compose` (hyphen) instead of `docker compose`.

If Neo4j is unreachable, set `GRAPH_STORE_BACKEND=fallback` to use the embedded NetworkX+SQLite store instead — no Docker required; reduced feature parity is acceptable for local iteration only:

```bash
# PowerShell
$env:GRAPH_STORE_BACKEND = "fallback"
python -m src.graph.healthcheck

# bash/zsh
export GRAPH_STORE_BACKEND=fallback
python -m src.graph.healthcheck
```

### Optional: remote Docker host

If Neo4j runs on another machine, point the app at it with `NEO4J_URI` (and credentials) in `.env`. To drive Compose against a remote Docker daemon, set `DOCKER_HOST` for that session (prefer TLS; avoid exposing an unauthenticated Docker TCP port on a LAN). Do not commit private hostnames or LAN IPs to the repo.
### Application

```bash
python -m venv .venv
.venv\Scripts\Activate.ps1          # Windows PowerShell
pip install -r requirements.txt
copy .env.example .env              # then edit .env (OPENAI_API_KEY, etc.)

python -m src.datagen.generate          # (re)generate the synthetic Meridian Retail Group dataset -> data/sample/
python -m src.ingestion.run             # idempotent ingestion into the graph store
python -m src.quality.run               # data-quality invariants against the ingested graph; exit 1 on error
uvicorn src.api.main:app --reload       # run the app -> http://127.0.0.1:8000
```

Environment variables are read from the project-root `.env` via `python-dotenv`
(`src/env_loader.py`). Process env vars still override `.env`. See `.env.example`
for the full list.

### Graph RAG (MVP2 open-ended Ask)

Closed 7-question templates always work without an LLM. For open-ended Ask, edit `.env`:

```
GRAPH_RAG_ENABLED=true
OPENAI_API_KEY=sk-...
# OPENAI_MODEL=gpt-4o-mini
```

Or set the same variables in the shell. If Graph RAG is enabled without `OPENAI_API_KEY`, Ask returns a clear configuration non-answer instead of calling the network.

### Hybrid Doc RAG (MVP3)

After regenerating and ingesting architecture docs, build the local vector index:

```bash
python -m src.datagen.generate
python -m src.ingestion.run
python -m src.retrieval.index_docs
```

Then enable fusion (requires Graph RAG + API key for live embeds/generation):

```
GRAPH_RAG_ENABLED=true
HYBRID_DOC_RAG_ENABLED=true
OPENAI_API_KEY=sk-...
# OPENAI_EMBEDDING_MODEL=text-embedding-3-small
# VECTOR_STORE_PATH=data/vectors/chunks.sqlite3
```

Vectors live under `data/vectors/` (SQLite). Re-run `index_docs` whenever docs change.

### Agentic Investigation (MVP4)

Separate from Ask. Enable in `.env`:

```
AGENTIC_INVESTIGATION_ENABLED=true
OPENAI_API_KEY=sk-...
# AGENTIC_MAX_TOOL_CALLS=3
```

Open `/investigate`, enter a change-impact style question naming a Meridian entity
(e.g. "What would be impacted if we retired Customer API v1?"). The run always
executes a required evidence skeleton, then up to N allowlisted tool calls, then
a grounded report with evidence and a step trace (`ADR-0007`).

### Advanced Intelligence (MVP5)

Deterministic risk, what-if, drift, and rationalization are always available
(no master kill-switch). Optional narrative:

```
INTELLIGENCE_NARRATIVE_ENABLED=true
OPENAI_API_KEY=sk-...
```

Open `/intelligence` for the hub (drift + rationalize links). Entity detail
pages show risk score and a retirement what-if panel (`ADR-0008`).

### Source–graph reconciliation (ADR-0009)

Ingestion always upserts, then diffs the graph against the current source
parse set and prints a **dry-run** of stale nodes/relationships:

```bash
python -m src.ingestion.run
```

Ingestion does **not** delete stale membership (no apply flag). To fully
reset Neo4j, use `docker-compose down -v` then re-ingest (see Rollback).

### Tests

```bash
pytest                          # unit + integration + data-quality tests
pytest evals/ -q                # golden dataset — must be 100% pass
ruff check .
```
## Deployment

Not applicable — MVP1 is local-first only, no deployment target (see `docs/00_project/PROJECT_CHARTER.md` constraints).

## Rollback

Not applicable for MVP1 (no deployed environment). Locally: `docker-compose down -v` to reset the graph store to empty, then re-run ingestion from `data/sample/`.

## Monitoring & alerting

None for MVP1. NL query requests are logged as structured JSON lines to a local log file (question, resolved intent, matched entities, latency) — see `docs/01_architecture/ARCHITECTURE.md`. No dashboard.

## Common operational tasks

| Task | Command |
|---|---|
| Regenerate synthetic dataset | `python -m src.datagen.generate` |
| Re-run ingestion (idempotent) | `python -m src.ingestion.run` |
| Check graph data quality | `python -m src.quality.run` |
| Reset the graph store | `docker-compose down -v && docker-compose up -d neo4j` |
| Enable open-ended Graph RAG Ask | Set `GRAPH_RAG_ENABLED=true` and `OPENAI_API_KEY` in `.env` (or the shell) |
| Index architecture docs for Hybrid Ask | `python -m src.retrieval.index_docs` (after datagen + ingestion) |
| Enable Hybrid Graph + Document RAG | Set `HYBRID_DOC_RAG_ENABLED=true` (requires Graph RAG + API key) |
| Enable Agentic Investigate | Set `AGENTIC_INVESTIGATION_ENABLED=true` and open `/investigate` |
| Open Intelligence hub | Visit `/intelligence` (risk on entity pages; drift + rationalize reports) |
| Enable intelligence narrative | Set `INTELLIGENCE_NARRATIVE_ENABLED=true` (+ `OPENAI_API_KEY`) |
| Dry-run stale graph membership | `python -m src.ingestion.run` (reports would-delete; does not delete) |

## Incidents

Not applicable for MVP1 (no production deployment, no on-call). If this changes in a later milestone, postmortems go under `docs/03_operations/` per `incident-postmortem-review`.
