# Runbook

Status: draft (will be updated as increments land — Docker/Neo4j section is accepted; app run commands fill in as `src/` is built)

Read by: `readme-runbook-documentation` skill.

## Local development

### Prerequisites

- Python 3.11+ (3.14 verified locally) with a virtualenv at `.venv/`.
- Docker CLI + Compose available locally (installed via `winget install Docker.DockerCLI Docker.DockerCompose` on Windows dev machines that don't run Docker Desktop themselves).
- Network access to the remote LAN Docker host at `192.168.4.52` (see below) — or willingness to fall back to the embedded NetworkX+SQLite store per `ADR-0001-graph-store-selection.md`.

### Remote Docker host connectivity (Neo4j runs here, not on the dev machine)

The dev machine does not run a local Docker daemon; Neo4j runs as a container on a separate Windows host on the LAN (`192.168.4.52`). One-time setup on **that host**:

1. Docker Desktop → Settings → General → enable "Expose daemon on tcp://localhost:2375 without TLS".
2. Forward the LAN-facing interface to the loopback daemon:
   ```powershell
   netsh interface portproxy add v4tov4 listenaddress=192.168.4.52 listenport=2375 connectaddress=127.0.0.1 connectport=2375
   ```
3. Open the port in Windows Firewall, scoped to the dev machine's IP only:
   ```powershell
   New-NetFirewallRule -DisplayName "Docker daemon (dev machine only)" -Direction Inbound -Protocol TCP -LocalPort 2375 -RemoteAddress 192.168.4.42 -Action Allow
   ```

From the **dev machine**, point the Docker CLI at the remote daemon for the current session:

```powershell
$env:DOCKER_HOST = "tcp://192.168.4.52:2375"
docker version         # confirms the remote daemon is reachable
docker-compose version # this environment installs docker-compose as a standalone binary, not a `docker compose` plugin — use the hyphenated form
```

Set `$env:DOCKER_HOST` in every new shell before running Docker/Compose commands against the graph store (or add it to your PowerShell profile).

### Graph store

```bash
# From the repo root, with DOCKER_HOST set as above:
docker-compose up -d neo4j
# Neo4j Browser: http://192.168.4.52:7474  |  Bolt: bolt://192.168.4.52:7687
# Default local dev credentials: neo4j / edi-local-dev (override via NEO4J_PASSWORD)

python -m src.graph.healthcheck    # verifies connectivity and bootstraps schema constraints
```

If the remote host is unreachable, set `GRAPH_STORE_BACKEND=fallback` (see `ADR-0001-graph-store-selection.md`) to use the embedded NetworkX+SQLite store instead — no Docker required, reduced feature parity is acceptable for local iteration only:

```bash
$env:GRAPH_STORE_BACKEND = "fallback"     # PowerShell; use export on bash/zsh
python -m src.graph.healthcheck
```

### Application

```bash
python -m venv .venv
.venv\Scripts\Activate.ps1          # Windows PowerShell
pip install -r requirements.txt
pip install -e ../enterprise-sdlc-mcp   # build-time MCP server, editable install into this project's venv

python -m src.datagen.generate          # (re)generate the synthetic Meridian Retail Group dataset -> data/sample/
python -m src.ingestion.run             # idempotent ingestion into the graph store
python -m src.quality.run               # data-quality invariants against the ingested graph; exit 1 on error
uvicorn src.api.main:app --reload       # run the app -> http://127.0.0.1:8000
```

*(Exact module paths above are the target shape from `docs/01_architecture/ARCHITECTURE.md`; update this section if an increment lands with a different entry-point name.)*

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
| Check for missing manifest keys | MCP tool `validate_manifest` |

## Incidents

Not applicable for MVP1 (no production deployment, no on-call). If this changes in a later milestone, postmortems go under `docs/03_operations/` per `incident-postmortem-review`.
