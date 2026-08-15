# 004 — Implementation Planning

Version: **1.0.0**
Status: **Approved / Frozen**
Derived from: **003-atomic-requirements v1.0.0 (Approved / Frozen)**
Approved: **2026-08-15**

## Purpose

Define the implementation decomposition, sequencing, migration strategy, ownership boundaries, handoffs and exit gates for satisfying the frozen atomic requirements.

This stage defines **how** the baseline repair is partitioned. Task-level Red → Green → Refactor increments are derived in `../005-tasks/`.

## Approved plan sequence

| Plan | Title | Direct prerequisites | Primary REQs |
|---|---|---|---:|
| [PLAN-001](PLAN-001.md) | Security guardrails and baseline characterization | 003 approved | 7 |
| [PLAN-002](PLAN-002.md) | Domain truth, canonical data and compatibility migration | PLAN-001 | 12 |
| [PLAN-003](PLAN-003.md) | Hexagonal boundaries and provider seams | PLAN-002 | 10 |
| [PLAN-004](PLAN-004.md) | Application ownership and persistence/search/operations decomposition | PLAN-003 | 11 |
| [PLAN-005](PLAN-005.md) | Functional and non-functional reconnection | PLAN-004 | 16 |
| [PLAN-006](PLAN-006.md) | Deployment, backup, documentation and operational-evidence closure | PLAN-005 | 10 |

```text
PLAN-001  security policy + characterization
    ↓
PLAN-002  domain/data truth + compatibility
    ↓
PLAN-003  ports/boundaries/composition seams
    ↓
PLAN-004  application ownership + responsibility split
    ↓
PLAN-005  functional/NFR acceptance
    ↓
PLAN-006  host evidence + current-doc convergence
```

The sequence is conservative for a brownfield system. Tightly coupled tasks may be implemented together only when each frozen requirement remains independently testable and the task dependency graph does not bypass a plan exit gate.

## Integration rules

1. Every `REQ-*` has exactly one primary plan owner.
2. The plan dependency graph is minimal: each plan depends directly on its immediate predecessor gate; earlier prerequisites are inherited transitively.
3. No primary owner precedes the primary plan of any direct `REQ-*` prerequisite.
4. Cross-plan concepts use handoffs rather than duplicate implementations.
5. Earlier plans establish semantics/primitives; later plans consume them and add only their owned layer of responsibility.
6. Host rehearsal may expose defects but does not silently redesign earlier architecture; defects return to the owning task/requirement.
7. New product functionality remains outside all six plans.

See [INTEGRATION-MAP.md](INTEGRATION-MAP.md) for concept ownership across plan boundaries and [REVIEW.md](REVIEW.md) for the planning gate audit.

## Task boundary

The plan package itself does not enumerate task-level code edits. The approved plans authorize derivation of `005-tasks`, which is the active downstream stage.
