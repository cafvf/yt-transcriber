# REQ-DATA-005 — Derived artifact association and authority

Version: **1.0.0**
Status: **Approved / Frozen**
Wave: **A**
Derived families: **DATA-DERIVED**
Behavior/spec sources: **UC-006..UC-009**
Dependencies: **REQ-DATA-001, REQ-DATA-003, REQ-DATA-004, REQ-SEC-003**

## Normative requirement

Derived artifacts SHALL be explicitly associated with their canonical transcript/Job identity, remain regenerable where practical, and SHALL never become an alternate source of transcript truth.

## Acceptance criteria

- AC-01: Summary, export and video derivative metadata identifies its canonical source association.
- AC-02: Regenerating a derived artifact does not mutate canonical transcript segments or provenance.
- AC-03: Deleting or failing to create a derivative does not invalidate an otherwise coherent canonical completed transcript.
- AC-04: Derived-artifact paths/metadata do not embed unrelated private staging information.

## Required evidence

- derived-artifact linkage tests
- summary/export/video workflow tests

## Scope guard

This requirement repairs or preserves the approved current baseline. It does not authorize semantic search, translation, an alternative ASR product feature, checkpoint resume, multi-user behavior, or knowledge-system integration.
