# REQ-DOM-005 — Versioned processing fingerprint and run provenance

Version: **1.0.0**
Status: **Approved / Frozen**
Wave: **A**
Derived families: **DOMAIN-PROVENANCE**
Behavior/spec sources: **D-016**
Dependencies: **REQ-DOM-001, REQ-DOM-002, REQ-DOM-003**

## Normative requirement

The system SHALL maintain one versioned processing-fingerprint concept for request-time policy that can materially affect canonical transcript production, and SHALL separately retain known actual run provenance describing the path/providers actually used.

## Acceptance criteria

- AC-01: Fingerprint excludes credentials, local paths, chat/user IDs, retention/log settings and unrelated operational values.
- AC-02: Fingerprint schema defines result-significant source-selection, audio, ASR, language, diarization and normalization policy that could affect the request's canonical result, including configured fallback policy even when a particular branch is not exercised.
- AC-03: Known actual source path, subtitle/ASR choice, backend/model/runtime and diarization/fallback facts are recorded as run provenance rather than silently inferred from fingerprint identity.
- AC-04: Historical missing provenance is represented as unknown/not-recorded.
- AC-05: Only one canonical fingerprint field-set/owner remains.

## Required evidence

- determinism tests
- config-field inclusion/exclusion tests
- snapshot/job provenance tests

## Brownfield deviation addressed

Current configuration-signature mechanisms overlap and current snapshot provenance is incomplete.

## Scope guard

This requirement repairs or preserves the approved current baseline. It does not authorize semantic search, translation, an alternative ASR product feature, checkpoint resume, multi-user behavior, or knowledge-system integration.
