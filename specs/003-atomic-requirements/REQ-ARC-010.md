# REQ-ARC-010 — Truthful configuration taxonomy and external compatibility

Version: **1.0.0**
Status: **Approved / Frozen**
Wave: **B**
Derived families: **ARCH-CONFIG**
Behavior/spec sources: **D-021, DD-003**
Dependencies: **REQ-ARC-001, REQ-DOM-005, REQ-SEC-008**

## Normative requirement

Internal configuration SHALL have a single truthful concern owner for each setting, keep credential configuration separated from ordinary behavior policy, and preserve approved operator-facing environment-variable compatibility while allowing source-neutral internal naming.

## Acceptance criteria

- AC-01: Existing approved operator environment-variable names remain accepted or have an explicit versioned migration.
- AC-02: Generic media/application settings use source-neutral internal names; source-specific names remain only for source-specific behavior.
- AC-03: Domain policy objects can be constructed without provider credential values.
- AC-04: Processing-fingerprint field selection has one canonical authority and does not diverge across duplicate configuration-signature implementations.

## Required evidence

- configuration compatibility tests
- fingerprint conformance tests
- secret-boundary architecture tests

## Brownfield deviation addressed

Configuration is monolithic and fingerprint/signature logic currently has overlapping authorities.

## Scope guard

This requirement repairs or preserves the approved current baseline. It does not authorize semantic search, translation, an alternative ASR product feature, checkpoint resume, multi-user behavior, or knowledge-system integration.
