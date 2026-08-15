# REQ-OPS-001 — Source-valid startup and restart reconciliation

Version: **1.0.0**
Status: **Approved / Frozen**
Wave: **E**
Derived families: **OPS-STARTUP**
Behavior/spec sources: **SS-001**
Dependencies: **REQ-DOM-002, REQ-DATA-001, REQ-DATA-002, REQ-ARC-003, REQ-NFR-001**

## Normative requirement

On startup the system SHALL deterministically requeue only source-valid pending work and reconcile interrupted active/delivery states to the approved terminal outcomes without claiming checkpoint resume.

## Acceptance criteria

- AC-01: Pending work is requeued only when required source-specific acquisition context and delivery/request context remain usable.
- AC-02: Legacy or incomplete pending work without recoverable payload becomes `failed`.
- AC-03: Interrupted `acquiring`, `converting`, `transcribing`, `diarizing` or `rendering` work becomes `failed`.
- AC-04: Interrupted `delivering` work becomes `delivery_failed`.
- AC-05: No mid-stage checkpoint resume is advertised or inferred.

## Required evidence

- startup-recovery unit tests
- SQLite integration recovery tests
- restart rehearsal evidence

## Scope guard

This requirement repairs or preserves the approved current baseline. It does not authorize semantic search, translation, an alternative ASR product feature, checkpoint resume, multi-user behavior, or knowledge-system integration.
