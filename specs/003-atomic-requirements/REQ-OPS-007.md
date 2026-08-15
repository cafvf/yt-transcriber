# REQ-OPS-007 — Reproducible host/staging readiness evidence

Version: **1.0.0**
Status: **Approved / Frozen**
Wave: **E**
Derived families: **OPS-EVIDENCE**
Behavior/spec sources: **OS-001..OS-004, SECURITY-AND-OPERATIONS §13**
Dependencies: **REQ-OPS-001, REQ-OPS-002, REQ-OPS-003, REQ-OPS-004, REQ-OPS-005, REQ-OPS-006, REQ-NFR-003, REQ-SEC-004**

## Normative requirement

Private-production readiness SHALL require sanitized reproducible host/staging evidence for systemd lifecycle, backup/restore, rollback, restart reconciliation and delivery-failed/manual recovery; helper-script tests alone SHALL not count as proof.

## Acceptance criteria

- AC-01: Each evidence record identifies revision, environment class, objective, actions, expected result, observed result and pass/fail decision.
- AC-02: Required real rehearsals run on the revision intended for closure or are explicitly repeated after a material change that invalidates prior evidence.
- AC-03: Evidence contains no reusable credentials or private transcript/provider payloads.
- AC-04: Readiness ledger distinguishes implemented/tested behavior from empirically rehearsed operation.

## Required evidence

- host/staging rehearsal records
- readiness-ledger conformance review

## Scope guard

This requirement repairs or preserves the approved current baseline. It does not authorize semantic search, translation, an alternative ASR product feature, checkpoint resume, multi-user behavior, or knowledge-system integration.
