# REQ-FUNC-007 — Generate a derived summary from canonical evidence

Version: **1.0.0**
Status: **Approved / Frozen**
Wave: **D**
Derived families: **FUNC-SUMMARY**
Behavior/spec sources: **UC-007**
Dependencies: **REQ-DATA-003, REQ-DATA-005, REQ-DATA-011, REQ-ARC-008, REQ-SEC-005, REQ-SEC-009, REQ-SEC-003, REQ-NFR-002**

## Normative requirement

The operator SHALL be able to generate a derived Markdown summary from canonical transcript evidence using the configured summary policy/backend without mutating canonical transcript state.

## Acceptance criteria

- AC-01: A disabled/unavailable configured summary capability reports an explicit unavailable outcome.
- AC-02: Chunking, input/output token budgets and application-level adaptive subdivision remain bounded and configurable.
- AC-03: Successful summary records available model, chunk/tokenizer and generation provenance appropriate to the current implementation.
- AC-04: Disclosure to a non-local text-generation endpoint follows the approved explicit external-service configuration/security boundary.
- AC-05: A successful summary becomes part of the current textual-search document where summary text is an approved indexed field.
- AC-06: Provider errors are sanitized.

## Required evidence

- summary application tests
- text-generation/tokenizer contract tests
- summary-search refresh tests
- security error tests

## Scope guard

This requirement repairs or preserves the approved current baseline. It does not authorize semantic search, translation, an alternative ASR product feature, checkpoint resume, multi-user behavior, or knowledge-system integration.
