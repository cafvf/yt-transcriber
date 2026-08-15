# 005 — Task Decomposition

Version: **1.0.0**
Status: **Approved / Frozen**
Derived from: **004-planning v1.0.0 (Approved / Frozen)**
Reference date: **2026-08-15**

## Purpose

Translate the six approved plans into concrete, dependency-ordered TDD increments without changing frozen requirement or plan semantics.

## Task model

Every one of the 66 frozen atomic REQs has exactly one **primary execution owner task**. Primary ownership means responsibility for closing that REQ's acceptance/evidence boundary; it does not require all implementation work for a cross-cutting invariant to occur in one oversized task.

The package uses four additional task roles:

- **support/foundation** — establishes a ratchet, seam or workflow migration used by a later REQ closure owner;
- **assurance/convergence owner** — owns cross-cutting verification and only implements residual behavior uniquely belonging to that NFR;
- **operational/evidence owner** — owns real procedures or empirical evidence without duplicating already-implemented application semantics;
- **plan gate** — verifies the frozen PLAN exit gate and routes failures back to owners; it adds no product behavior.

## Counts

| Plan | Primary REQ owners | Support/foundation | Plan gate | Total |
|---|---:|---:|---:|---:|
| PLAN-001 | 7 | 1 | 1 | 9 |
| PLAN-002 | 12 | 0 | 1 | 13 |
| PLAN-003 | 10 | 3 | 1 | 14 |
| PLAN-004 | 11 | 5 | 1 | 17 |
| PLAN-005 | 16 | 0 | 1 | 17 |
| PLAN-006 | 10 | 0 | 1 | 11 |
| **Total** | **66** | **9** | **6** | **81** |

## Execution sequence

```text
PLAN-001 baseline + security tasks → gate
    ↓
PLAN-002 domain/data/compatibility tasks → gate
    ↓
PLAN-003 foundations → seam migrations → closures → gate
    ↓
PLAN-004 workflow-by-workflow decomposition → closures/assurance → gate
    ↓
PLAN-005 functional/NFR acceptance → gate
    ↓
PLAN-006 operational procedures/evidence/docs → closure gate
```

## Execution rules

1. Respect `DEPENDENCIES.md`; a later plan cannot start before the prior gate.
2. Run characterization before structural refactor when current behavior must be preserved.
3. Use Red → Green → Refactor for reproducible behavior. Host-only requirements may use a failing preflight/rehearsal criterion rather than a fake unit Red.
4. Support tasks never redefine frozen REQ semantics.
5. Closure/assurance/gate failures reopen the behavior-owning task instead of creating a parallel implementation.
6. Reuse valid operational evidence as defined in `INTEGRATION-MAP.md`; do not repeat dangerous/expensive rehearsals solely for bookkeeping.
7. Do not add semantic search, translation, alternative ASR product behavior, checkpoint resume, multi-user support, new media sources or knowledge-system integrations during this milestone.
8. Record the tests/checks/evidence actually run for each completed task.

## Navigation

- `TASK-INDEX.md` — all task IDs, roles and primary REQs.
- `DEPENDENCIES.md` — executable ordering.
- `TRACEABILITY.md` — frozen REQ → primary task mapping.
- `INTEGRATION-MAP.md` — handoffs, deliberate non-merges, failure routing and evidence reuse.
- `REVIEW.md` — coherence review and corrections.
- `APPROVAL.md` / `FREEZE.md` — normative task-stage approval.
