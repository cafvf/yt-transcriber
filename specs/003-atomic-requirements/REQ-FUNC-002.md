# REQ-FUNC-002 — Process media through truthful subtitle, ASR and diarization paths

Version: **1.0.0**
Status: **Approved / Frozen**
Wave: **D**
Derived families: **FUNC-PROCESS**
Behavior/spec sources: **UC-001, DD-005, DD-006**
Dependencies: **REQ-FUNC-001, REQ-DOM-002, REQ-DOM-003, REQ-ARC-013, REQ-ARC-005, REQ-ARC-006, REQ-DATA-004**

## Normative requirement

Accepted media SHALL follow the approved source-specific shortcut/common-processing path and produce truthful canonical transcript evidence, falling back from unsuitable YouTube subtitles to audio/ASR and never bypassing language or duration constraints through fabricated metadata.

## Acceptance criteria

- AC-01: An eligible manual or accepted automatic non-translated subtitle may skip ASR after integrity/quality checks.
- AC-02: Missing, unsuitable or corrupt subtitle falls back to the approved audio/ASR path.
- AC-03: Unknown source language stays unknown until an operator constraint or truthful source/ASR observation exists.
- AC-04: Without an explicit operator language constraint, an independently observed ASR language outside the allowlist is rejected rather than relabeled.
- AC-05: With an explicit operator language constraint, the constraint may drive forced decoding but any independent observed language/confidence remains separately attributable and is not rewritten.
- AC-06: Unknown duration is established as within limit before expensive ASR/diarization or the request is rejected.
- AC-07: The audio path converts, selects runtime policy, transcribes, diarizes and persists the required canonical structured/Markdown evidence.

## Required evidence

- pipeline behavior tests
- subtitle fallback/integrity tests
- language/duration regression tests
- canonical-persistence failure tests

## Scope guard

This requirement repairs or preserves the approved current baseline. It does not authorize semantic search, translation, an alternative ASR product feature, checkpoint resume, multi-user behavior, or knowledge-system integration.
