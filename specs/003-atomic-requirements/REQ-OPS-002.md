# REQ-OPS-002 — Automatic completed-Job retention execution

Version: **1.0.0**
Status: **Approved / Frozen**
Wave: **E**
Derived families: **OPS-RETENTION**
Behavior/spec sources: **SS-002**
Dependencies: **REQ-DATA-010, REQ-DATA-004, REQ-ARC-009, REQ-NFR-002**

## Normative requirement

The system SHALL apply configured automatic retention to eligible volatile artifacts of completed Jobs without removing canonical transcript evidence or leaving false durable availability references.

## Acceptance criteria

- AC-01: Configured retention count/policy is enforced deterministically.
- AC-02: Canonical structured snapshot and Markdown required by approved history, rename and export behavior are preserved.
- AC-03: Removed volatile-media/log references are cleared or marked unavailable coherently.
- AC-04: Retention failure is sanitized/recorded and does not retroactively change a successfully completed primary-delivery outcome.

## Required evidence

- retention execution tests
- reference-truth tests
- failure-isolation tests

## Scope guard

This requirement repairs or preserves the approved current baseline. It does not authorize semantic search, translation, an alternative ASR product feature, checkpoint resume, multi-user behavior, or knowledge-system integration.
