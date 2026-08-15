# PLAN-004 — Application ownership and persistence/search/operations decomposition

Version: **1.0.0**
Status: **Approved / Frozen**
Derived from: **003-atomic-requirements v1.0.0**
Prerequisite plans: **PLAN-003** *(earlier gates inherited transitively)*
Approved: **2026-08-15**

## Goal

Move portable workflows out of Telegram/infrastructure hotspots and separate lifecycle persistence, indexing/search, summary policy, operational policy and execution coordination behind the ports established by PLAN-003, using small reversible refactors protected by characterization and contract tests.

## Primary requirement scope

- `REQ-DATA-005` — Derived artifact association and authority
- `REQ-DATA-006` — Bounded private operational logs
- `REQ-DATA-007` — Reconstructible cache lifecycle
- `REQ-DATA-011` — Textual-search index data and lifecycle
- `REQ-ARC-002` — Application workflow ownership and thin Telegram transport
- `REQ-ARC-003` — Application-owned execution, queue, cancellation and recovery coordination
- `REQ-ARC-007` — Separated lifecycle persistence, indexing and search capabilities
- `REQ-ARC-008` — Application summary policy and infrastructure text-generation transport
- `REQ-ARC-009` — Operational policy separated from external I/O mechanisms
- `REQ-NFR-001` — Deterministic lifecycle reliability and failure isolation
- `REQ-NFR-005` — Cohesive, testable and reversible baseline refactoring

## Implementation approach

1. Extract application-owned submission/dedup/reprocess, queue/cancellation/recovery and primary-delivery outcome coordination while retaining Telegram-only parsing/presentation/UI state at the adapter.
2. Move history selection and other portable numbered-history rules out of `infrastructure.telegram` without merging history with textual search.
3. Separate lifecycle persistence from canonical transcript storage and textual indexing/search; make index refresh an explicit application collaboration triggered by approved changes.
4. Make derived-artifact association explicit and keep textual index data rebuildable from approved canonical/derived sources.
5. Move summary transcript preparation, chunking/reduction/prompt/output policy into application; keep HTTP/auth/tokenizer/model-library mechanisms in infrastructure behind PLAN-003 capabilities.
6. Put health/error/retention/cache policy behind application probes/stores while moving direct filesystem/network/subprocess/log mechanisms to infrastructure capabilities.
7. Give operational logs bounded retention/read semantics and keep readiness evidence under an explicit evidence-retention path rather than accidental log survival.
8. Apply the decomposition one workflow at a time, retaining characterization tests until replacement application tests and contract tests prove equivalence.
9. Finish with Telegram adapter responsibility reduction and removal of superseded collaborations/abstractions only after consumers have moved.

## Ownership boundary and handoff

PLAN-004 owns **workflow placement and responsibility decomposition**. It does not re-specify domain truth from PLAN-002 or provider seams from PLAN-003. It hands off:

- end-to-end operator behavior and resource/responsiveness acceptance to PLAN-005;
- automatic host lifecycle/recovery/retention rehearsals and documentation convergence to PLAN-006.

History and search remain separate capabilities; transcript exports and video derivatives remain separate; operational policy and operational I/O remain distinct even when one composition graph wires them together.

## Migration and compatibility constraints

- Do not rewrite all adapters at once; move one portable workflow at a time behind characterization tests.
- Do not make JobRepository responsible for hidden index filesystem reads.
- Do not make the Telegram adapter the new composition root.
- Do not add parallel sanitizer/path/secret policies; consume PLAN-001 guardrails.
- Do not use temporary duplication as a permanent second source of policy truth.

## Exit gate

- Portable application workflows execute without Telegram classes.
- Lifecycle repository tests no longer require hidden search-index side effects.
- FTS/fallback integration tests remain green through the split.
- Summary application tests run with fake text generation/tokenizer/store.
- Operational application tests use fake probes/stores and contain no direct infrastructure imports or direct filesystem/network/subprocess operations.
- Telegram adapter responsibility is materially reduced and no new god-object replaces it.
- Refactors are covered by characterization/contract/architecture evidence and remain reversible at plan-sized increments.

## Not tasks

The numbered approach above defines migration order and design constraints, not a task checklist. Concrete files, red tests, implementation increments, commits and task ownership are defined in `../005-tasks/`.
