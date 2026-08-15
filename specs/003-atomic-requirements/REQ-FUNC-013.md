# REQ-FUNC-013 — Text-search completed history

Version: **1.0.0**
Status: **Approved / Frozen**
Wave: **D**
Derived families: **FUNC-SEARCH**
Behavior/spec sources: **UC-005**
Dependencies: **REQ-DATA-011, REQ-ARC-007, REQ-SEC-003**

## Normative requirement

The operator SHALL be able to perform operator-scoped textual search over approved completed-history fields using SQLite FTS5 when available or the approved deterministic bounded textual fallback when FTS5 is unavailable.

## Acceptance criteria

- AC-01: Search is limited to completed Jobs belonging to the authorized operator scope.
- AC-02: FTS5 absence activates the approved bounded textual fallback without changing to semantic/vector search.
- AC-03: Search documents reflect approved transcript metadata/text, aliases and summary text according to the textual-index contract.
- AC-04: Returned snippets are compact, sanitized and do not expose private staging paths.

## Required evidence

- SQLite FTS integration tests
- fallback tests
- search privacy/sanitization tests

## Scope guard

This requirement repairs or preserves the approved current baseline. It does not authorize semantic search, translation, an alternative ASR product feature, checkpoint resume, multi-user behavior, or knowledge-system integration.
