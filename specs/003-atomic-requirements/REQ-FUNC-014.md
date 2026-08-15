# REQ-FUNC-014 — Generate YouTube MP4 with selectable subtitles

Version: **1.0.0**
Status: **Approved / Frozen**
Wave: **D**
Derived families: **FUNC-VIDEO**
Behavior/spec sources: **UC-009**
Dependencies: **REQ-DOM-001, REQ-DATA-002, REQ-DATA-003, REQ-DATA-005, REQ-ARC-006, REQ-SEC-005, REQ-SEC-009, REQ-SEC-003, REQ-NFR-002**

## Normative requirement

For an eligible completed YouTube Job, the operator SHALL be able to generate an MP4 derivative containing selectable subtitles from canonical transcript evidence without changing canonical transcript state.

## Acceptance criteria

- AC-01: Non-YouTube Jobs are rejected for this derivative.
- AC-02: Subtitles are generated from canonical structured evidence and current aliases.
- AC-03: Source video is reacquired from canonical YouTube identity through the YouTube adapter; authentication cookies remain boundary-confined.
- AC-04: Configured duration and output/download size limits are enforced.
- AC-05: Missing structured evidence or unavailable source produces an explicit derivative failure without mutating the completed Job.

## Required evidence

- video-derivative tests
- ffmpeg command/integration tests
- source/security boundary tests

## Scope guard

This requirement repairs or preserves the approved current baseline. It does not authorize semantic search, translation, an alternative ASR product feature, checkpoint resume, multi-user behavior, or knowledge-system integration.
