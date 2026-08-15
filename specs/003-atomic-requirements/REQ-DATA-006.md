# REQ-DATA-006 — Bounded private operational logs

Version: **1.0.0**
Status: **Approved / Frozen**
Wave: **A**
Derived families: **DATA-OPSLOG**
Behavior/spec sources: **UC-010, UC-011, OPS-EVIDENCE**
Dependencies: **REQ-SEC-003, REQ-SEC-004**

## Normative requirement

Operational error, audit and application logs SHALL be private, sanitized, queryable for the approved diagnostic/evidence purpose, and subject to explicit bounded retention so recent-error inspection does not require unbounded accumulation.

## Acceptance criteria

- AC-01: Central operational logs have configured rotation, retention or compaction semantics.
- AC-02: `/lasterror` reads a bounded recent window and does not require loading indefinitely growing history.
- AC-03: Audit records omit transcript, prompt and provider payload bodies except for separately approved local-debug behavior.
- AC-04: Readiness evidence that must outlive ordinary log retention is stored/retained under its explicit evidence policy rather than relying on accidental log survival.

## Required evidence

- log-retention tests
- bounded-read tests
- sanitization tests
- evidence-storage review

## Scope guard

This requirement repairs or preserves the approved current baseline. It does not authorize semantic search, translation, an alternative ASR product feature, checkpoint resume, multi-user behavior, or knowledge-system integration.
