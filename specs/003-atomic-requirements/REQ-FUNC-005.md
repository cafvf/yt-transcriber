# REQ-FUNC-005 — Browse and retrieve completed history

Version: **1.0.0**
Status: **Approved / Frozen**
Wave: **D**
Derived families: **FUNC-HISTORY**
Behavior/spec sources: **UC-004**
Dependencies: **REQ-DATA-001, REQ-DATA-003, REQ-DATA-004, REQ-ARC-007, REQ-SEC-003**

## Normative requirement

The operator SHALL be able to browse completed history and retrieve saved canonical Markdown using deterministic current positional ordering without treating those positions as durable identifiers or silently reprocessing missing evidence.

## Acceptance criteria

- AC-01: Displayed numeric indexes are positions over the current completed ordering and may change when that ordering changes.
- AC-02: History is scoped to the authorized operator and completed in-scope Jobs.
- AC-03: `/last` or indexed retrieval returns the saved Markdown associated with the selected completed Job.
- AC-04: Missing/unreadable required canonical history evidence is reported explicitly and does not trigger reprocessing.

## Required evidence

- history ordering/selection tests
- missing-artifact tests
- privacy scoping tests

## Scope guard

This requirement repairs or preserves the approved current baseline. It does not authorize semantic search, translation, an alternative ASR product feature, checkpoint resume, multi-user behavior, or knowledge-system integration.
