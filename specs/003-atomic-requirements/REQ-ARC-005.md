# REQ-ARC-005 — Diarization capability, fallback and credential isolation

Version: **1.0.0**
Status: **Approved / Frozen**
Wave: **B**
Derived families: **ARCH-DIAR**
Behavior/spec sources: **UC-001, ARCHITECTURE §4**
Dependencies: **REQ-ARC-012, REQ-ARC-004, REQ-SEC-008, REQ-DOM-005**

## Normative requirement

Application diarization SHALL use a provider-neutral capability contract with explicit fallback/error semantics and provenance, while provider authentication is configured inside concrete adapters/composition rather than passed through the application port.

## Acceptance criteria

- AC-01: The application diarization port has no provider credential parameter such as `hf_token`.
- AC-02: Primary/fallback adapters implement common speaker-segment result/error semantics.
- AC-03: Fallback conditions are explicit and tested.
- AC-04: Known actual diarization backend/model/fallback facts are available for run provenance.

## Required evidence

- shared diarization contract tests
- fallback regression tests
- architecture credential scan

## Scope guard

This requirement repairs or preserves the approved current baseline. It does not authorize semantic search, translation, an alternative ASR product feature, checkpoint resume, multi-user behavior, or knowledge-system integration.
