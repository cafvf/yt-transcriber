# REQ-ARC-003 — Application-owned execution, queue, cancellation and recovery coordination

Version: **1.0.0**
Status: **Approved / Frozen**
Wave: **B**
Derived families: **ARCH-EXECUTION**
Behavior/spec sources: **UC-001..UC-004, SS-001**
Dependencies: **REQ-ARC-002, REQ-ARC-012, REQ-DOM-002, REQ-DATA-001**

## Normative requirement

Sequential execution, queue state, cooperative cancellation, restart coordination and primary-delivery outcome coordination SHALL be application-owned capabilities independent of Telegram transport mechanics.

## Acceptance criteria

- AC-01: Queue behavior can be driven through application tests without Telegram classes.
- AC-02: Queue state mutations and Job lifecycle persistence remain coherent.
- AC-03: Cancellation token propagation is transport-independent.
- AC-04: Startup recovery consumes application request context and source-valid recoverability rules rather than Telegram payload objects.

## Required evidence

- queue/cancellation application tests
- startup-recovery tests
- architecture tests

## Scope guard

This requirement repairs or preserves the approved current baseline. It does not authorize semantic search, translation, an alternative ASR product feature, checkpoint resume, multi-user behavior, or knowledge-system integration.
