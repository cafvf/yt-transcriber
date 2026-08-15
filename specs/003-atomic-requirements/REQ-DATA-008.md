# REQ-DATA-008 — Backward-compatible persisted representations and migrations

Version: **1.0.0**
Status: **Approved / Frozen**
Wave: **A**
Derived families: **DATA-COMPAT**
Behavior/spec sources: **D-015, DD-003**
Dependencies: **REQ-DATA-001, REQ-DATA-003**

## Normative requirement

Persistence and schema changes during baseline repair SHALL preserve readable historical Jobs/snapshots and use explicit tested migration or compatibility decoding instead of silent destructive rewriting.

## Acceptance criteria

- AC-01: Legacy `downloading` status remains readable as semantic `acquiring`.
- AC-02: Snapshot schema v1 remains readable.
- AC-03: Nullable/non-YouTube `video_id` semantics remain compatible.
- AC-04: Migration or compatibility decoding preserves segments, timestamps, speaker labels, source metadata and current re-renderability.
- AC-05: Any destructive migration requires explicit backup/rollback evidence before deployment.

## Required evidence

- representative legacy SQLite integration tests
- snapshot compatibility tests
- migration/rollback tests

## Scope guard

This requirement repairs or preserves the approved current baseline. It does not authorize semantic search, translation, an alternative ASR product feature, checkpoint resume, multi-user behavior, or knowledge-system integration.
