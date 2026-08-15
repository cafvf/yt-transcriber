# REQ-DOM-001 — Source-neutral media identity

Version: **1.0.0**
Status: **Approved / Frozen**
Wave: **A**
Derived families: **DOMAIN-MEDIA**
Behavior/spec sources: **UC-001, D-015**
Dependencies: **upstream approved specifications only**

## Normative requirement

The domain SHALL represent media identity by source type plus a source-appropriate canonical identity without inventing YouTube identity for non-YouTube media or conflating identity with acquisition location.

## Acceptance criteria

- AC-01: YouTube identity retains video_id/canonical-URL semantics.
- AC-02: Telegram audio has a distinct private source identity and no synthetic video_id.
- AC-03: A local staging/download path is not the canonical media identity.
- AC-04: Internal generic-media names are source-neutral; source-specific names remain only for genuinely source-specific concepts.

## Required evidence

- domain unit tests
- persistence round-trip compatibility tests

## Scope guard

This requirement repairs or preserves the approved current baseline. It does not authorize semantic search, translation, an alternative ASR product feature, checkpoint resume, multi-user behavior, or knowledge-system integration.
