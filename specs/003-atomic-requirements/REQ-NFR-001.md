# REQ-NFR-001 — Deterministic lifecycle reliability and failure isolation

Version: **1.0.0**
Status: **Approved / Frozen**
Wave: **C**
Derived families: **NFR-RELIABILITY**
Behavior/spec sources: **UC-001, UC-003, SS-001**
Dependencies: **REQ-DOM-002, REQ-DATA-004**

## Normative requirement

Equivalent lifecycle events SHALL produce deterministic valid outcomes, failures in derived or diagnostic operations SHALL remain isolated from canonical completed Jobs, and repeatable recovery actions SHALL be idempotent where repeated execution is possible.

## Acceptance criteria

- AC-01: Invalid lifecycle transitions fail deterministically.
- AC-02: Repeated startup reconciliation does not repeatedly mutate already reconciled terminal state.
- AC-03: Failure of a derived/diagnostic operation does not retroactively mutate a canonical completed Job.
- AC-04: Canonical persistence failure cannot be reported as successful completion.

## Required evidence

- lifecycle/state-machine tests
- restart idempotency tests
- derived-failure isolation tests

## Scope guard

This requirement repairs or preserves the approved current baseline. It does not authorize semantic search, translation, an alternative ASR product feature, checkpoint resume, multi-user behavior, or knowledge-system integration.
