# REQ-ARC-008 — Application summary policy and infrastructure text-generation transport

Version: **1.0.0**
Status: **Approved / Frozen**
Wave: **B**
Derived families: **ARCH-TEXTGEN**
Behavior/spec sources: **D-018, UC-007**
Dependencies: **REQ-ARC-012, REQ-SEC-005, REQ-SEC-006, REQ-SEC-009, REQ-DATA-003**

## Normative requirement

Summary transcript selection, chunking/reduction, prompt/output policy and application-level recovery decisions SHALL be application-owned, while HTTP/auth/provider translation and concrete tokenizer/model-library integration SHALL remain infrastructure implementations of narrow capabilities.

## Acceptance criteria

- AC-01: Application summary workflow runs with fake canonical store, tokenizer and text-generation capability.
- AC-02: Network client contains no transcript-selection, chunking or summary-output business policy.
- AC-03: Application owns whether/how a failed or timed-out summary unit is subdivided/reduced; adapter owns the mechanism of an individual transport request and its transport timeout.
- AC-04: Text-generation capability is justified by current summarization needs and does not pre-specify translation semantics.

## Required evidence

- application summary unit tests
- text-generation/tokenizer adapter contract tests
- architecture tests

## Scope guard

This requirement repairs or preserves the approved current baseline. It does not authorize semantic search, translation, an alternative ASR product feature, checkpoint resume, multi-user behavior, or knowledge-system integration.
