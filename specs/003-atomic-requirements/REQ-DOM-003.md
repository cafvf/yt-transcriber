# REQ-DOM-003 — Truthful transcript and language semantics

Version: **1.0.0**
Status: **Approved / Frozen**
Wave: **A**
Derived families: **DOMAIN-TRANSCRIPT**
Behavior/spec sources: **UC-001, DD-005**
Dependencies: **upstream approved specifications only**

## Normative requirement

Canonical Transcript SHALL preserve truthful segment, speaker, language, language-source and confidence semantics; unknown, forced and independently observed facts SHALL remain distinguishable and SHALL not be fabricated or silently relabeled.

## Acceptance criteria

- AC-01: Segments require non-empty text and a positive time span.
- AC-02: Source/transcript language may remain unknown until a truthful source exists.
- AC-03: An independently ASR-observed language outside the allowlist is never rewritten as another allowed language.
- AC-04: An operator-requested/forced language constraint is distinguishable from an independently observed language and from the confidence of that observation.
- AC-05: When forced decoding provides no independent confidence for the forced language, canonical evidence records confidence as unknown/not-provided rather than borrowing an unrelated score.
- AC-06: Subtitle-derived transcripts record subtitle provenance distinctly from ASR-derived transcripts.

## Required evidence

- domain invariant tests
- ASR/subtitle forced-language regression tests

## Brownfield deviation addressed

WhisperX currently maps unsupported detected language to `allowed_languages[0]`; YouTube metadata defaults an unknown language to English.

## Scope guard

This requirement repairs or preserves the approved current baseline. It does not authorize semantic search, translation, an alternative ASR product feature, checkpoint resume, multi-user behavior, or knowledge-system integration.
