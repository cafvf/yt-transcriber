# REQ-DATA-004 — Canonical completion consistency and artifact-reference truth

Version: **1.0.0**
Status: **Approved / Frozen**
Wave: **A**
Derived families: **DATA-INTEGRITY**
Behavior/spec sources: **UC-001, SS-002, OS-004**
Dependencies: **REQ-DATA-001, REQ-DATA-002, REQ-DATA-003, REQ-DATA-010**

## Normative requirement

The system SHALL not advance a Job toward successful primary delivery/completion unless required canonical evidence is durably coherent, and durable metadata SHALL never claim an artifact is available after it was not created, became unreadable, or was deleted.

## Acceptance criteria

- AC-01: Structured-snapshot persistence failure prevents successful transcript completion.
- AC-02: A partial canonical-write failure has an explicit failure outcome and does not leave lifecycle/reference metadata claiming successful canonical completion.
- AC-03: Retention and cleanup clear or truthfully mark references to removed artifacts.
- AC-04: Missing or corrupt required canonical evidence causes an explicit derived/history failure rather than silent reconstruction from Markdown or media.

## Required evidence

- failure-injection tests for snapshot/Markdown writes
- retention reference tests
- corruption/missing-evidence tests

## Brownfield deviation addressed

`RenderMarkdownStep` currently swallows snapshot-save failure; retention can leave stale Job paths.

## Scope guard

This requirement repairs or preserves the approved current baseline. It does not authorize semantic search, translation, an alternative ASR product feature, checkpoint resume, multi-user behavior, or knowledge-system integration.
