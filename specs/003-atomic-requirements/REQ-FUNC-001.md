# REQ-FUNC-001 — Submit supported media and explicitly reprocess as a new Job

Version: **1.0.0**
Status: **Approved / Frozen**
Wave: **D**
Derived families: **FUNC-SOURCE**
Behavior/spec sources: **UC-001**
Dependencies: **REQ-SEC-001, REQ-SEC-005, REQ-SEC-009, REQ-DOM-001, REQ-DATA-001, REQ-DATA-002, REQ-ARC-002, REQ-ARC-003, REQ-NFR-002**

## Normative requirement

The authorized operator SHALL be able to submit supported YouTube references and Telegram audio/voice/audio-document media and SHALL be able to explicitly reprocess a YouTube source as a distinct new Job, subject to source validation, queue capacity and the frozen active/pending deduplication policy.

## Acceptance criteria

- AC-01: Supported Telegram audio, voice, audio-document and YouTube URL paths are accepted when source-specific constraints are satisfied.
- AC-02: Unsupported source/media type, explicit unsupported language request, source-specific size violation or full queue is rejected explicitly.
- AC-03: A YouTube submission is an active duplicate only when the current/pending queue already contains the same canonical video identity with the same requested-language value; terminal historical Jobs do not themselves block a new submission.
- AC-04: Explicit `/redo` creates a distinct new Job when accepted and never reopens or mutates a terminal historical Job; it remains subject to the same active/pending duplicate guard.

## Required evidence

- submission/dedup/reprocess application tests
- Telegram adapter conformance tests

## Brownfield deviation addressed

Current deduplication exists inside the Telegram adapter and compares only active/pending `video_id + requested_language`; the application layer must preserve that frozen behavior while taking ownership of the policy.

## Scope guard

This requirement repairs or preserves the approved current baseline. It does not authorize semantic search, translation, an alternative ASR product feature, checkpoint resume, multi-user behavior, or knowledge-system integration.
