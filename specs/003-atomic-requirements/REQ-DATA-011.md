# REQ-DATA-011 — Textual-search index data and lifecycle

Version: **1.0.0**
Status: **Approved / Frozen**
Wave: **A**
Derived families: **DATA-SEARCH**
Behavior/spec sources: **UC-005, D-019**
Dependencies: **REQ-DATA-001, REQ-DATA-003, REQ-DATA-004, REQ-DATA-005, REQ-SEC-003**

## Normative requirement

Textual-search documents SHALL be treated as private derived data explicitly associated with completed canonical Jobs/transcripts and SHALL remain coherent with approved transcript/alias/summary changes.

## Acceptance criteria

- AC-01: Search documents identify the canonical Job/transcript source without indexing private staging paths.
- AC-02: Deleting or making a Job non-searchable removes or invalidates its search document.
- AC-03: Speaker-alias and successful-summary changes refresh the affected textual-search state when those fields are part of the approved search document.
- AC-04: Search data is rebuildable from approved canonical/derived sources and is never alternate transcript truth.

## Required evidence

- SQLite FTS/fallback integration tests
- rename/summary index-refresh tests
- search privacy tests

## Scope guard

This requirement repairs or preserves the approved current baseline. It does not authorize semantic search, translation, an alternative ASR product feature, checkpoint resume, multi-user behavior, or knowledge-system integration.
