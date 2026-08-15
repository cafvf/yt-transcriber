# REQ-OPS-006 — Manual artifact recovery after delivery failure

Version: **1.0.0**
Status: **Approved / Frozen**
Wave: **E**
Derived families: **OPS-RECOVERY**
Behavior/spec sources: **OS-004**
Dependencies: **REQ-FUNC-003, REQ-FUNC-010, REQ-DATA-004, REQ-SEC-003**

## Normative requirement

For `delivery_failed` or interrupted-delivery scenarios, the operator SHALL be able to determine whether preserved local artifacts actually exist and recover them manually without reopening the terminal Job or leaking secrets/private payloads through diagnostics.

## Acceptance criteria

- AC-01: `/lasterror` or equivalent operational data reflects actual artifact availability.
- AC-02: Recovery uses local protected artifacts and documented operator steps.
- AC-03: No implicit resend or Job reopen occurs.
- AC-04: A missing or retention-purged artifact is reported unavailable rather than recoverable.

## Required evidence

- manual-recovery workflow tests
- delivery-failed host/staging rehearsal

## Scope guard

This requirement repairs or preserves the approved current baseline. It does not authorize semantic search, translation, an alternative ASR product feature, checkpoint resume, multi-user behavior, or knowledge-system integration.
