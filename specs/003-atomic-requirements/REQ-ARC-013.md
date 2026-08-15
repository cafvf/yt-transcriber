# REQ-ARC-013 — Backend-neutral ASR contract

Version: **1.0.0**
Status: **Approved / Frozen**
Wave: **B**
Derived families: **ARCH-ASR**
Behavior/spec sources: **UC-001, DD-005, ARCHITECTURE §9.1**
Dependencies: **REQ-ARC-012, REQ-ARC-004, REQ-DOM-003, REQ-DOM-005**

## Normative requirement

The application ASR contract SHALL express backend-independent transcription inputs, constraints, progress/cancellation and structured results rather than WhisperX/CTranslate2-specific device, compute-type or model-library parameters.

## Acceptance criteria

- AC-01: Generic ASR request carries transcribable audio, requested/forced language constraint when present, cancellation/progress and an application processing profile as needed.
- AC-02: ASR result can represent independently observed language/confidence separately from a forced/user-requested language constraint.
- AC-03: Concrete adapter translates the application processing profile into backend-specific device/compute/model arguments.
- AC-04: Unsupported independent language observations are surfaced truthfully and are never silently relabeled to an allowed language.

## Required evidence

- shared ASR contract tests
- WhisperX adapter tests
- language/provenance regression tests

## Scope guard

This requirement repairs or preserves the approved current baseline. It does not authorize semantic search, translation, an alternative ASR product feature, checkpoint resume, multi-user behavior, or knowledge-system integration.
