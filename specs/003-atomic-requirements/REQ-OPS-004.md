# REQ-OPS-004 — Credential-free backup and validated restore procedure

Version: **1.0.0**
Status: **Approved / Frozen**
Wave: **E**
Derived families: **OPS-BACKUP**
Behavior/spec sources: **OS-002**
Dependencies: **REQ-DATA-009, REQ-OPS-003**

## Normative requirement

The operator SHALL have a repeatable backup/restore procedure for the approved standard backup set that excludes reusable credentials/cookies and validates restored database/canonical-artifact relationships before resuming normal operation.

## Acceptance criteria

- AC-01: Backup uses a consistency-preserving SQLite copy and protected storage.
- AC-02: Standard procedure does not copy `.env`, the systemd secret environment file or authentication cookies.
- AC-03: Restore occurs with the service stopped or in isolated staging.
- AC-04: Post-restore database-open plus approved health/status/history checks are captured.

## Required evidence

- backup-helper tests
- real backup/restore rehearsal evidence

## Scope guard

This requirement repairs or preserves the approved current baseline. It does not authorize semantic search, translation, an alternative ASR product feature, checkpoint resume, multi-user behavior, or knowledge-system integration.
