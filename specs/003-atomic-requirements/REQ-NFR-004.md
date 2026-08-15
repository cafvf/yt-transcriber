# REQ-NFR-004 — Supported runtime portability and environment-gated evidence

Version: **1.0.0**
Status: **Approved / Frozen**
Wave: **C**
Derived families: **NFR-PORTABILITY**
Behavior/spec sources: **QUALITY §§2,9,11; PRODUCT baseline**
Dependencies: **REQ-ARC-004, REQ-ARC-011, REQ-SEC-006**

## Normative requirement

Supported Python/Linux/runtime expectations SHALL be explicit and reproducible, and tests requiring host-specific capabilities SHALL be clearly classified, gated and reported rather than silently treated as passed.

## Acceptance criteria

- AC-01: Supported Python versions match project metadata and CI configuration.
- AC-02: Supported Linux/system dependencies are documented and can be checked through health/preflight evidence.
- AC-03: Every currently inventoried environment-gated contract test retains its evidence role or has an explicit replacement before removal.
- AC-04: An unavailable environment-gated capability produces a visible skip/unavailability reason rather than a false pass.

## Required evidence

- pyproject/CI/documentation conformance tests
- inventory mapping for environment-gated tests
- host-specific test reports

## Scope guard

This requirement repairs or preserves the approved current baseline. It does not authorize semantic search, translation, an alternative ASR product feature, checkpoint resume, multi-user behavior, or knowledge-system integration.
