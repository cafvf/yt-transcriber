# REQ-FUNC-003 — Primary and derivative delivery outcomes

Version: **1.0.0**
Status: **Approved / Frozen**
Wave: **D**
Derived families: **FUNC-DELIVERY**
Behavior/spec sources: **UC-001..UC-012, OS-004**
Dependencies: **REQ-SEC-001, REQ-SEC-003, REQ-DOM-002, REQ-DATA-004, REQ-ARC-002**

## Normative requirement

Delivery SHALL distinguish primary-transcription completion from retrieval/derived-artifact sends: only primary transcript delivery controls the original Job `delivering→completed|delivery_failed` terminal outcome.

## Acceptance criteria

- AC-01: Required primary artifacts remain locally recoverable when primary delivery retries exhaust, subject to retention policy.
- AC-02: Successful primary delivery marks the Job `completed`.
- AC-03: Failure to send history, summary, export or video for an already completed Job does not retroactively change that completed lifecycle.
- AC-04: Delivery errors are sanitized and recorded as operational errors where appropriate.

## Required evidence

- delivery/retry tests
- derived-delivery failure isolation tests
- manual-recovery evidence

## Scope guard

This requirement repairs or preserves the approved current baseline. It does not authorize semantic search, translation, an alternative ASR product feature, checkpoint resume, multi-user behavior, or knowledge-system integration.
