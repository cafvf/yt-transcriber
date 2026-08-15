# REQ-DATA-003 — Dual canonical transcript persistence and explicit linkage

Version: **1.0.0**
Status: **Approved / Frozen**
Wave: **A**
Derived families: **DATA-TRANSCRIPT, DATA-MARKDOWN**
Behavior/spec sources: **UC-001, UC-004..UC-009, DD-001**
Dependencies: **REQ-DOM-003, REQ-DOM-004, REQ-DOM-005**

## Normative requirement

A successful transcript SHALL persist a versioned structured snapshot and its canonical Markdown rendering from the same logical Transcript, and the durable Job/application record SHALL have an explicit association with the canonical structured evidence.

## Acceptance criteria

- AC-01: New structured writes carry an explicit schema version.
- AC-02: Existing snapshot schema v1 remains readable.
- AC-03: Telegram evidence does not invent YouTube identity.
- AC-04: New persistence does not rely solely on `md_path` stem/slug to discover the canonical structured snapshot.
- AC-05: Structured consumers load structured evidence rather than parse Markdown when structured evidence exists.

## Required evidence

- snapshot round-trip/legacy tests
- explicit-link persistence tests
- rename/export/summary contract tests

## Brownfield deviation addressed

Current Job→snapshot linkage is inferred from Markdown slug/path convention.

## Scope guard

This requirement repairs or preserves the approved current baseline. It does not authorize semantic search, translation, an alternative ASR product feature, checkpoint resume, multi-user behavior, or knowledge-system integration.
