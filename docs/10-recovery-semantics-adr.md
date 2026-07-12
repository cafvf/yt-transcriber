# ADR — Recovery Semantics for durable queue and restart recovery

Date: 2026-07-08
Status: Accepted for Phase 2 implementation

## Context

The approved production-maturity roadmap requires durable queue/restart
recovery before the bot can be called private single-operator production-ready.
Before this ADR, the operational queue was only in memory and lost pending work
on process restart.

Phase 2 must define:

- the persistence source of truth for restart recovery;
- duplicate-prevention/idempotence rules;
- how each lifecycle state behaves at startup;
- whether active jobs resume from checkpoints or restart from a safe boundary;
- the migration strategy for SQLite without adding heavy migration tooling.

## Decision

### 1. Source of truth

The source of truth is **job-status-driven recovery using the existing `jobs`
table**, not a separate persistent `queue` table.

Rationale:

- the bot is single-operator and strictly sequential;
- enqueue order can be reconstructed from `requested_at`;
- the repo already persists job lifecycle state;
- this keeps the Phase 2 diff smaller and avoids introducing a second queue
  state machine before it is operationally necessary.

### 2. Persisted restart payload

Each job must persist enough request metadata to recreate a safe pending queue
entry after restart:

- `source_url`
- `requested_chat_id`
- `requested_language`
- `artifact_policy`
- `config_signature` (already persisted)

For v1, `artifact_policy` is the explicit string `audio+markdown`.

### 3. Duplicate-prevention and idempotence

- Runtime deduplication remains keyed by `video_id + requested_language` for
  jobs already active or enqueued in the current process.
- Startup recovery re-enqueues only persisted `pending` jobs with sufficient
  payload metadata.
- Startup recovery is **process-idempotent**: a given adapter instance applies
  recovery at most once.
- Across real restarts, pending jobs may be re-enqueued again because the
  in-memory queue starts empty and the persisted `pending` rows remain the
  source of truth until they actually run.

### 4. Startup state handling

- `pending` with full restart payload:
  - re-enqueue in ascending `requested_at` order.
- `pending` without full restart payload:
  - mark `failed` with a sanitized recovery reason because the job cannot be
    resumed safely.
- Active processing states
  (`downloading`, `converting`, `transcribing`, `diarizing`, `rendering`):
  - mark `failed` with a sanitized “interrupted by restart” reason;
  - do **not** try to resume from partial internal checkpoints in Phase 2.
- `delivering`:
  - mark `delivery_failed` with a sanitized restart reason;
  - preserve local artifact paths when present so `/lasterror` can help recovery.
- `completed`, `failed`, `cancelled`, `delivery_failed`:
  - unchanged at startup.

### 5. Retry/resume policy

Phase 2 does **not** resume active jobs from mid-pipeline checkpoints and does
not auto-retry interrupted active jobs from the beginning. It only:

- requeues safe `pending` jobs; and
- repairs interrupted in-flight states into explicit terminal/retryable states.

### 6. Migration strategy

No Alembic in Phase 2.

SQLite migrations use a **lightweight additive bootstrap migrator** in the
repository initialization path:

- create missing tables for fresh databases;
- inspect the existing `jobs` schema;
- `ALTER TABLE ... ADD COLUMN ...` for additive Phase 2 columns when missing.

This keeps migrations local, reviewable, and dependency-free.

## Consequences

### Positive

- Pending work survives process restarts when enough payload metadata exists.
- Interrupted jobs do not remain stuck forever in non-terminal states.
- The restart contract stays explicit without introducing a separate queue table.
- The diff preserves the current single-operator architecture.

### Negative

- No checkpoint-level resume inside ASR/diarization/download steps.
- Pending rows remain the durable source of truth, so same-process startup
  recovery must be guarded to avoid duplicate in-memory enqueue.
- If a legacy pending row lacks payload metadata, restart recovery must fail it
  explicitly instead of guessing.
