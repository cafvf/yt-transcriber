# REQ-FUNC-011 — Safely clear reconstructible cache

Version: **1.0.0**
Status: **Approved / Frozen**
Wave: **D**
Derived families: **FUNC-MAINT**
Behavior/spec sources: **UC-012**
Dependencies: **REQ-ARC-009, REQ-DATA-007, REQ-SEC-007, REQ-NFR-007**

## Normative requirement

The operator SHALL be able to delete only the approved reconstructible model/tokenizer cache scope, with path containment and truthful feedback, without touching canonical/history data.

## Acceptance criteria

- AC-01: Unsafe, ambiguous or out-of-scope cache root is refused.
- AC-02: Missing cache is a benign empty/no-op result.
- AC-03: Partial deletion failures are sanitized and recorded.
- AC-04: Canonical Job/transcript/summary/history data remains intact.

## Required evidence

- cache command tests
- path/symlink containment tests
- async responsiveness test

## Scope guard

This requirement repairs or preserves the approved current baseline. It does not authorize semantic search, translation, an alternative ASR product feature, checkpoint resume, multi-user behavior, or knowledge-system integration.
