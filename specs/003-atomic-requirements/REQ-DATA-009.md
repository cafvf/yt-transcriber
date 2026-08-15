# REQ-DATA-009 — Credential-free standard backup and restore integrity

Version: **1.0.0**
Status: **Approved / Frozen**
Wave: **A**
Derived families: **DATA-BACKUP**
Behavior/spec sources: **OS-002, D-024**
Dependencies: **REQ-DATA-001, REQ-DATA-002, REQ-DATA-003, REQ-DATA-005, REQ-DATA-006, REQ-SEC-002, REQ-SEC-003, REQ-SEC-007**

## Normative requirement

The standard operational backup SHALL capture the minimum durable data required to restore approved history and artifact relationships while excluding reusable provider credentials, secret-bearing environment files and authentication cookies.

## Acceptance criteria

- AC-01: The documented standard backup set explicitly lists included and excluded data classes.
- AC-02: SQLite backup is obtained through a consistency-preserving mechanism.
- AC-03: Restore preserves canonical transcript links, history and database integrity.
- AC-04: Reusable credentials, secret-bearing env files and authentication cookies are reprovisioned separately rather than copied into the standard backup.

## Required evidence

- backup-helper tests
- real backup/restore rehearsal
- post-restore health/status/list evidence

## Brownfield deviation addressed

Current runbook copies systemd env and `.env` into the standard backup and must converge with the approved security specification.

## Scope guard

This requirement repairs or preserves the approved current baseline. It does not authorize semantic search, translation, an alternative ASR product feature, checkpoint resume, multi-user behavior, or knowledge-system integration.
