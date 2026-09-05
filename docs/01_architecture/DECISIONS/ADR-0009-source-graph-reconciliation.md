# ADR-0009: Source–graph delete reconciliation

Status: Accepted

## Context

Ingestion has been upsert-only (`MERGE`): re-runs update existing natural
keys but never retract nodes or relationships when source rows disappear.
Stale graph facts can diverge from current Meridian sources. Operators need
visibility into membership drift before any destructive cleanup.

## Decision

1. **After upsert**, compute an **expected set** of node ids and relationship
   keys `(source_id, target_id, rel_type)` from the same parse result used
   for writing. Diff against `get_all_nodes` / `get_all_relationships`.
2. **Always report** a dry-run `ReconciliationReport` (would-delete lists).
3. **No apply path in v1:** there is no `--reconcile-apply` flag and no
   `RECONCILE_APPLY` env. Ingestion **never** hard-deletes based on this
   report. GraphStore may still expose `delete_*` for tests/future use, but
   the ingestion CLI/pipeline does not call them for reconciliation.
4. **Cross-source rule:** a node is expected if any source in this run emits
   its id.
5. Semantic drift (lifecycle / `REPLACED_BY` / unresolved) stays separate
   (`ADR-0008`).

## Consequences

- **Easier:** local Neo4j cannot be emptied by a recon flag by accident.
- **Easier:** operators still see stale membership after every ingest.
- **Harder:** cleaning stale nodes still requires a full graph reset
  (`docker-compose down -v` + re-ingest) or a future opt-in apply ADR.
- **Supersedes** “deletion never reported” — reporting is in; apply remains
  deferred.
