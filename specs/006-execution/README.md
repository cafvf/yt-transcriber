# Execution Evidence

Status: **Active / non-normative execution record**
Started: **2026-08-15**

This directory records implementation-phase execution evidence derived from the
approved and frozen SDD chain. It does not redefine the Constitution, baseline,
use cases, requirement tree, atomic requirements, plans, or tasks.

Normative precedence remains:

```text
constitution
  -> 000-baseline
  -> 001-use-cases
  -> 002-requirements
  -> 003-atomic-requirements
  -> 004-planning
  -> 005-tasks
```

Execution records may report evidence, failures, deferred environment checks,
and phase progress. A later implementation discovery that conflicts with frozen
intent must be classified and resolved through the approved change process; it
must not be silently normalized in this directory.

## Execution phases

See `PHASES.md` for the operational grouping of approved tasks.

Current execution state:

- F0 — executable baseline: **Verified / Closed**;
- F1 — security guardrails: **Verified / Closed**;
- F2 — domain and data truth: **Verified / Closed**;
- F3 — hexagonal boundaries: **In progress — TASK-P03-001..007 and TASK-P03-010 locally verified; TASK-P03-008 next**.

Detailed evidence is recorded in `F0-BASELINE.md`, `F1-SECURITY.md`,
`F2-DOMAIN-DATA.md`, and `F3-HEXAGONAL-SEAMS.md`.
