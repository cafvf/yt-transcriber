# REQ-DATA-002 — Volatile media ownership and lifecycle

Version: **1.0.0**
Status: **Approved / Frozen**
Wave: **A**
Derived families: **DATA-MEDIA**
Behavior/spec sources: **UC-001, UC-003, DD-006**
Dependencies: **REQ-DOM-001, REQ-DOM-004, REQ-SEC-007**

## Normative requirement

Staged, downloaded and converted media SHALL have explicit ownership, validity and cleanup semantics across validation rejection, cancellation, processing failure and restart.

## Acceptance criteria

- AC-01: Rejected or cancelled Telegram staging is removed when no longer required for an approved recovery path.
- AC-02: Unknown duration is represented as unknown, not zero, and is resolved by a bounded source-appropriate mechanism before expensive ASR/diarization or the request is rejected.
- AC-03: Temporary acquisition/conversion outputs are associated with the owning Job/request context rather than selected by arbitrary directory age.
- AC-04: Cleanup never removes canonical transcript evidence or media owned by unrelated work.

## Required evidence

- media lifecycle unit/integration tests
- ffmpeg-gated evidence
- cancellation/rejection cleanup tests

## Scope guard

This requirement repairs or preserves the approved current baseline. It does not authorize semantic search, translation, an alternative ASR product feature, checkpoint resume, multi-user behavior, or knowledge-system integration.
