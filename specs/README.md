# Specifications

Status: **Active specification framework**
Constitution: **v1.0.0 (Ratified 2026-08-15)**
Baseline reference: **2026-08-15**
Approved baseline: **000-baseline v1.0.0 (Approved 2026-08-15)**
Approved atomic requirements: **003-atomic-requirements v1.0.0 (Approved / Frozen)**
Approved planning: **004-planning v1.0.0 (Approved / Frozen)**
Approved tasks: **005-tasks v1.0.0 (Approved / Frozen)**
Active stage: **TDD implementation under approved task dependency order**

This directory contains the normative specification layer for `yt-transcriber`.

The project is brownfield: substantial behavior, tests, documentation, and operational practice existed before this specification structure. The purpose of this directory is to reconstruct the current contract from evidence, make architectural intent explicit, identify deviations, and only then derive use cases, requirements, implementation plans, and tasks.

## Authority model

Normative intent follows this precedence:

1. ratified `specs/constitution.md`
2. ratified specifications in `specs/`
3. ratified ADRs, when they do not conflict with higher-level specifications
4. executable evidence: tests, architecture checks, conformance checks, and operational rehearsals
5. implementation
6. user/operator documentation
7. historical records and gate reports

During brownfield reconstruction, implementation, tests, runtime behavior, historical records, and operator evidence are inputs used to discover the baseline. A behavior found in code is not automatically a requirement: it may be an accident, defect, obsolete behavior, or architectural deviation.

Once a specification is ratified, a deliberate behavior change requires a corresponding specification change before or alongside test and code changes.


## Versioning and approval

The Constitution uses semantic versioning under its governance rules.

Baseline and feature specifications use draft `0.x` versions until approved. The first approved form of a specification becomes `1.0.0`; later changes are versioned according to compatibility and scope. Specifications may be approved independently, but a dependent specification cannot be approved while relying on an unresolved contradiction in an upstream specification.

Approval is explicit. Merely committing a draft file does not make it normative.

## Specification states

- **Draft** — under analysis; not yet normative.
- **Approved** — accepted as normative intent.
- **Superseded** — replaced by a newer approved specification.
- **Historical** — retained only as evidence of a past state.

## Development flow

```text
CONSTITUTION
    ↓
BASELINE SPECIFICATIONS
    ↓
CLARIFICATIONS / DECISIONS
    ↓
USE CASES
    ↓
REQUIREMENT TREE
    ↓
ATOMIC REQUIREMENTS
    ↓
PLAN
    ↓
TASKS
    ↓
TDD IMPLEMENTATION
    ↓
CONFORMANCE / OPERATIONAL EVIDENCE
    ↓
CONVERGENCE
```

The approved baseline, frozen use-case stage, frozen requirement tree, atomic requirements, planning, and task decomposition are closed. Productive remediation may now proceed only through the approved `005-tasks` dependency order and TDD gates.

## Approved baseline package

`specs/000-baseline/` is approved as **v1.0.0** and contains:

- `PRODUCT.md`
- `ARCHITECTURE.md`
- `DOMAIN.md`
- `DATA-AND-ARTIFACTS.md`
- `QUALITY.md`
- `SECURITY-AND-OPERATIONS.md`
- `DECISIONS.md`
- `OPEN-DECISIONS.md`

## Frozen use-case stage

`specs/001-use-cases/` is approved/frozen as v1.0.1 and defines the behavioral scope used for requirement derivation.

## Approved requirement-tree stage

`specs/002-requirements/` is approved/frozen as v1.0.0 and defines the 66 requirement families, conceptual dependencies, evidence inventory, traceability, and current-code audit coverage.

## Approved atomic-requirement stage

`specs/003-atomic-requirements/` is approved/frozen as **v1.0.0** and defines the normative `REQ-*` obligations, acceptance criteria, evidence expectations, semantic review, dependencies, and derivation decisions used by implementation planning.


## Approved planning stage

`specs/004-planning/` is approved/frozen as **v1.0.0**. The six plans cover all 66 frozen atomic REQs exactly once as primary ownership, contain no prerequisite ownership inversions, and define explicit cross-plan handoffs.

## Approved task stage

`specs/005-tasks/` is approved/frozen as **v1.0.0**. It defines 66 primary REQ-owner tasks, 9 support/foundation tasks and 6 plan gates, with explicit cross-plan handoffs, closure ownership, failure routing and operational-evidence reuse.

## What does not belong here yet

Productive source-code changes must not bypass the approved task graph. Each change is driven by an approved task using characterization and Red → Green → Refactor as applicable. New product capabilities remain outside the baseline milestone until the final PLAN-006 closure gate passes.

## Relationship with legacy documentation

Existing `README.md` and `docs/` remain valuable evidence and operational documentation. Historical gate reports, patch notes, and evidence remain historical even when terminology changes. Current canonical documentation will later be reconciled with approved specifications without falsifying the historical record.

## Current SDD stage

- `000-baseline`: **v1.0.0 Approved**
- `001-use-cases`: **v1.0.1 Approved / Frozen**
- `002-requirements`: **v1.0.0 Approved / Frozen**
- `003-atomic-requirements`: **v1.0.0 Approved / Frozen**
- `004-planning`: **v1.0.0 Approved / Frozen**
- `005-tasks`: **v1.0.0 Approved / Frozen**
- implementation: **authorized only through approved tasks; not yet started by this documentation package**
