# REQ-SEC-007 — Filesystem containment and restrictive permissions

Version: **1.0.0**
Status: **Approved / Frozen**
Wave: **A**
Derived families: **SEC-FILES**
Behavior/spec sources: **UC-012, OS-002, OS-004**
Dependencies: **REQ-SEC-003**

## Normative requirement

Filesystem writes and destructive operations SHALL remain within explicitly owned/configured storage locations, and sensitive operational artifacts SHALL use restrictive permissions appropriate to their sensitivity.

## Acceptance criteria

- AC-01: Clear/delete operations resolve and validate their target against the approved owned root before deletion.
- AC-02: A symlink or resolved target that escapes the approved root is refused for destructive operations.
- AC-03: Backup, evidence and secret-bearing files created by operational helpers use restrictive permissions.
- AC-04: Canonical evidence belonging to unrelated Jobs is never removed by cache/media cleanup.

## Required evidence

- path-containment and symlink-escape tests
- permission assertions in operational helpers
- host/staging rehearsal evidence

## Scope guard

This requirement repairs or preserves the approved current baseline. It does not authorize semantic search, translation, an alternative ASR product feature, checkpoint resume, multi-user behavior, or knowledge-system integration.
