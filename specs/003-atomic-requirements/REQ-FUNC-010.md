# REQ-FUNC-010 — Inspect the latest relevant operational error

Version: **1.0.0**
Status: **Approved / Frozen**
Wave: **D**
Derived families: **FUNC-DIAG**
Behavior/spec sources: **UC-011**
Dependencies: **REQ-ARC-009, REQ-DATA-006, REQ-NFR-003, REQ-SEC-004, REQ-NFR-007**

## Normative requirement

The operator SHALL be able to inspect the latest relevant failed/delivery-failed Job or operational error with truthful local-artifact availability and no implicit resend or terminal-state mutation.

## Acceptance criteria

- AC-01: No-error outcome is explicit.
- AC-02: Selection compares the most recent failed/delivery-failed Job timestamp with the most recent operator-scoped operational-error timestamp and returns the newer record; ties preserve the current operational-error precedence.
- AC-03: `delivery_failed` recovery information reports only artifacts that actually exist and remain available.
- AC-04: Raw prompts, provider bodies and secrets are not disclosed.
- AC-05: Inspection does not mutate terminal Job state.

## Required evidence

- last-error precedence tests
- artifact-existence tests
- sanitization tests
- async responsiveness test

## Scope guard

This requirement repairs or preserves the approved current baseline. It does not authorize semantic search, translation, an alternative ASR product feature, checkpoint resume, multi-user behavior, or knowledge-system integration.
