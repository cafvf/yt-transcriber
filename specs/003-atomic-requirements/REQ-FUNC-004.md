# REQ-FUNC-004 — Observe queue/status and cancel scoped work

Version: **1.0.0**
Status: **Approved / Frozen**
Wave: **D**
Derived families: **FUNC-CONTROL**
Behavior/spec sources: **UC-002, UC-003**
Dependencies: **REQ-DOM-002, REQ-DATA-001, REQ-ARC-003, REQ-ARC-002**

## Normative requirement

The operator SHALL receive a consistent read-only view of active/pending work and SHALL be able to cooperatively cancel the active Job, pending Jobs, or both without changing unrelated work.

## Acceptance criteria

- AC-01: Status/queue inspection does not reorder or mutate work.
- AC-02: Pending cancellation removes the targeted queue entry and persists the approved cancelled outcome.
- AC-03: Active cancellation propagates a cooperative signal and need not interrupt an already-running external operation instantaneously.
- AC-04: Cancelled pending Telegram staging is cleaned when no approved recovery path still requires it.
- AC-05: Empty/no-match outcomes are truthful.

## Required evidence

- queue/status tests
- pending/active cancellation tests
- staging cleanup tests

## Scope guard

This requirement repairs or preserves the approved current baseline. It does not authorize semantic search, translation, an alternative ASR product feature, checkpoint resume, multi-user behavior, or knowledge-system integration.
