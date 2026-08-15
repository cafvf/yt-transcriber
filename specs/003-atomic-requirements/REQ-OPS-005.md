# REQ-OPS-005 — Versioned upgrade and rollback procedure

Version: **1.0.0**
Status: **Approved / Frozen**
Wave: **E**
Derived families: **OPS-UPGRADE**
Behavior/spec sources: **OS-003**
Dependencies: **REQ-DATA-008, REQ-NFR-006, REQ-OPS-004, REQ-OPS-003**

## Normative requirement

The operator SHALL be able to upgrade and roll back the application with recorded Git revision, compatible persisted data, pre-change backup and post-change validation, without silent destructive migration.

## Acceptance criteria

- AC-01: Pre-upgrade revision and backup are recorded.
- AC-02: Migration/compatibility checks pass before the production upgrade proceeds.
- AC-03: Rollback restores the prior code revision and, when required by a migration, compatible prior data through the approved recovery path.
- AC-04: Health/status/journal validation is recorded after upgrade and rollback.

## Required evidence

- upgrade/rollback helper tests
- real host/staging rollback rehearsal

## Scope guard

This requirement repairs or preserves the approved current baseline. It does not authorize semantic search, translation, an alternative ASR product feature, checkpoint resume, multi-user behavior, or knowledge-system integration.
