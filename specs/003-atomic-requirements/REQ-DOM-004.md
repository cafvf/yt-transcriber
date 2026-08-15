# REQ-DOM-004 — Canonical and derived artifact taxonomy

Version: **1.0.0**
Status: **Approved / Frozen**
Wave: **A**
Derived families: **DOMAIN-ARTIFACT**
Behavior/spec sources: **D-012, DATA-AND-ARTIFACTS**
Dependencies: **REQ-DOM-003**

## Normative requirement

The system SHALL maintain an explicit artifact taxonomy distinguishing canonical machine-readable transcript evidence, canonical human-readable Markdown, derived artifacts, volatile media, operational data and reconstructible cache so lifecycle actions cannot silently change artifact authority.

## Acceptance criteria

- AC-01: The versioned structured transcript is canonical machine-readable evidence.
- AC-02: Markdown is the canonical human-readable rendering of that structured evidence.
- AC-03: Summary/export/search/video outputs are derived and never become alternate transcript truth.
- AC-04: Volatile media and reconstructible cache may be removed only under their explicit lifecycle policy.

## Required evidence

- artifact-classification conformance tests
- traceability review

## Scope guard

This requirement repairs or preserves the approved current baseline. It does not authorize semantic search, translation, an alternative ASR product feature, checkpoint resume, multi-user behavior, or knowledge-system integration.
