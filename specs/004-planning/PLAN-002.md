# PLAN-002 — Domain truth, canonical data and compatibility migration

Version: **1.0.0**
Status: **Approved / Frozen**
Derived from: **003-atomic-requirements v1.0.0**
Prerequisite plans: **PLAN-001**
Approved: **2026-08-15**

## Goal

Repair domain truth and durable canonical-data semantics before large responsibility refactors: source-neutral identity, enforced Job state graph, truthful language/duration/provenance, explicit request/delivery context, explicit canonical transcript linkage, completion consistency, backward-compatible persisted representations, and completed-Job retention classification.

## Primary requirement scope

- `REQ-DOM-001` — Source-neutral media identity
- `REQ-DOM-002` — Explicit Job lifecycle state machine
- `REQ-DOM-003` — Truthful transcript and language semantics
- `REQ-DOM-004` — Canonical and derived artifact taxonomy
- `REQ-DOM-005` — Versioned processing fingerprint and run provenance
- `REQ-DATA-001` — Durable Job state and restart/delivery request context
- `REQ-DATA-002` — Volatile media ownership and lifecycle
- `REQ-DATA-003` — Dual canonical transcript persistence and explicit linkage
- `REQ-DATA-004` — Canonical completion consistency and artifact-reference truth
- `REQ-DATA-008` — Backward-compatible persisted representations and migrations
- `REQ-DATA-010` — Completed-Job retention policy and canonical preservation
- `REQ-NFR-006` — External behavior and data compatibility during baseline repair

## Implementation approach

1. Introduce characterization tests for the legal Job graph and all legacy persisted statuses before enforcing transitions.
2. Represent `unknown` language/duration explicitly; preserve `/pt`/`/en` as forced constraints without fabricating independent observations or confidence.
3. Separate pure Job identity/lifecycle from Telegram delivery routing at the model boundary while initially preserving legacy persisted columns through compatibility projection.
4. Establish one processing-fingerprint authority and separately retain actual run provenance; include only policy relevant to the path/result being fingerprinted.
5. Add an explicit durable canonical structured-transcript reference instead of discovering snapshot ownership solely from Markdown slug conventions.
6. Make successful primary completion contingent on coherent structured snapshot + canonical Markdown evidence; persist availability references only after corresponding artifacts actually exist/read correctly.
7. Keep schema changes additive/compatibility-first until legacy round-trip and rollback evidence exists.
8. Separate volatile staging/media lifecycle from completed-Job retention classification.
9. Preserve frozen commands, aliases, env names and readable historical data while internal source-neutral taxonomy changes.

## Ownership boundary and handoff

PLAN-002 owns **semantic truth and durable compatibility**, not application ports or orchestration. It hands off:

- purpose-specific transcript/persistence/runtime ports to PLAN-003;
- persistence/search class decomposition and operational policy orchestration to PLAN-004;
- operator workflow acceptance to PLAN-005;
- backup/restore and host migration rehearsal to PLAN-006.

PLAN-003 and PLAN-004 may reorganize code around this model but must not reopen the frozen lifecycle, provenance, canonical-artifact or compatibility semantics.

## Migration and compatibility constraints

- Do not delete legacy columns/status values in the first migration simply because internal names change.
- Do not parse Markdown to reconstruct structured truth when a structured snapshot is required.
- Do not introduce checkpoint/resume semantics.
- Do not conflate persisted delivery routing with pure Job identity.
- Do not use synthetic language/duration values as compatibility defaults.

## Exit gate

- Parameterized legal/illegal lifecycle tests pass.
- Legacy DB/snapshot fixtures remain readable.
- Language and duration regressions prove no synthetic English/zero or silent ASR relabeling.
- Job/request context compatibility preserves restart/delivery semantics while the domain model is transport-neutral.
- Canonical write failure cannot lead to successful primary completion.
- Retention classification preserves canonical evidence and artifact-reference truth.
- Frozen operator/data compatibility evidence passes for all changed persisted representations.

## Not tasks

The numbered approach above defines migration order and design constraints, not a task checklist. Concrete files, red tests, implementation increments, commits and task ownership are defined in `../005-tasks/`.
