# REQ-NFR-003 — Actionable privacy-aware observability

Version: **1.0.0**
Status: **Approved / Frozen**
Wave: **C**
Derived families: **NFR-OBS**
Behavior/spec sources: **UC-002, UC-010, UC-011, OS-001..OS-004**
Dependencies: **REQ-DATA-006, REQ-SEC-004**

## Normative requirement

Operational observability SHALL make lifecycle, health, failure and rehearsal decisions diagnosable with minimal private content and stable event/status semantics.

## Acceptance criteria

- AC-01: Audit events identify operation, Job/opaque correlation, stage and outcome without transcript bodies.
- AC-02: Health/error reports distinguish blockers, warnings and recoverable artifact availability.
- AC-03: Logs provide enough sanitized context for the operator to choose a documented next action.
- AC-04: Evidence records identify revision/environment/result without credentials or private transcript payloads.

## Required evidence

- observability contract tests
- health/lasterror tests
- evidence-review checklist

## Scope guard

This requirement repairs or preserves the approved current baseline. It does not authorize semantic search, translation, an alternative ASR product feature, checkpoint resume, multi-user behavior, or knowledge-system integration.
