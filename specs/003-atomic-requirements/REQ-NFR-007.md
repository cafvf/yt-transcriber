# REQ-NFR-007 — Non-blocking Telegram transport responsiveness

Version: **1.0.0**
Status: **Approved / Frozen**
Wave: **C**
Derived families: **NFR-RESOURCE**
Behavior/spec sources: **UC-001..UC-012, QUALITY**
Dependencies: **REQ-ARC-002, REQ-NFR-002**

## Normative requirement

Long synchronous CPU, filesystem, subprocess or provider work initiated by Telegram handlers SHALL not monopolize the Telegram async event loop; the transport SHALL remain responsive to independent lightweight control/interaction work within the limits of the sequential processing model.

## Acceptance criteria

- AC-01: Known long synchronous processing is executed outside the Telegram event-loop thread or exposed through an asynchronous capability.
- AC-02: Finite subprocess/provider waits do not block unrelated async callbacks solely because a synchronous function was called directly from a handler.
- AC-03: Progress/control callbacks can continue to be serviced according to the frozen sequential-processing contract while expensive work runs.
- AC-04: Tests demonstrate that representative slow duration/subprocess or application work does not block an independent event-loop tick.

## Required evidence

- async responsiveness tests
- regression test analogous to ffprobe non-blocking coverage

## Scope guard

This requirement repairs or preserves the approved current baseline. It does not authorize semantic search, translation, an alternative ASR product feature, checkpoint resume, multi-user behavior, or knowledge-system integration.
