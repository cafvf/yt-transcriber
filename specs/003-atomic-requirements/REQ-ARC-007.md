# REQ-ARC-007 — Separated lifecycle persistence, indexing and search capabilities

Version: **1.0.0**
Status: **Approved / Frozen**
Wave: **B**
Derived families: **ARCH-PERSIST**
Behavior/spec sources: **D-019**
Dependencies: **REQ-ARC-012, REQ-DATA-001, REQ-DATA-003, REQ-DATA-005, REQ-DATA-011**

## Normative requirement

Lifecycle persistence, canonical transcript storage, indexing transformation and search query semantics SHALL be distinct application capabilities even when a temporary infrastructure class implements more than one interface.

## Acceptance criteria

- AC-01: `JobRepository.save` has no hidden transcript/summary filesystem reads solely to update search state.
- AC-02: Index refresh is an explicit application-owned operation triggered by approved canonical/derived changes, not a hidden lifecycle-repository side effect.
- AC-03: Search capability may use FTS5 or the bounded fallback without changing lifecycle persistence semantics.
- AC-04: Contract/integration tests distinguish lifecycle persistence, indexing and search behavior.

## Required evidence

- contract/integration tests for each capability
- SQLite FTS/fallback tests

## Brownfield deviation addressed

Current SQLAlchemy repository mixes lifecycle persistence, indexing/search and artifact loading.

## Scope guard

This requirement repairs or preserves the approved current baseline. It does not authorize semantic search, translation, an alternative ASR product feature, checkpoint resume, multi-user behavior, or knowledge-system integration.
