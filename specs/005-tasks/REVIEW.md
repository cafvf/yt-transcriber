# Task Coherence Review

Version: **1.0.0**
Status: **Passed after correction**
Date: **2026-08-15**

## Review basis

`005-tasks` was reviewed against:

- `specs/constitution.md` v1.0.0;
- approved `000-baseline` product, architecture, domain, data, quality and security/operations specifications;
- frozen `001-use-cases` v1.0.1;
- frozen `002-requirements` v1.0.0;
- frozen `003-atomic-requirements` v1.0.0, including dependencies and derivation decisions;
- frozen `004-planning` v1.0.0, including plan ownership, handoffs and exit gates;
- current brownfield component boundaries already identified by the approved audit.

## Initial result

The 0.1.0 task draft had correct REQ coverage and an acyclic dependency graph, but it was **not approved as written**. The review found execution-level ambiguities that could create redundant implementation or false closure.

## Corrections made

### 1. Reproducible starting baseline received an explicit owner

The plans required characterization before structural change, but the draft relied on individual tasks and the PLAN-001 gate to infer the global starting baseline.

Added `TASK-P01-000` to capture revision, default quality/security gates, frozen interface characterization and integration-test classification before behavior-changing remediation begins.

### 2. Cross-cutting architecture requirements now have foundation and closure tasks

`REQ-ARC-001` and `REQ-ARC-012` could not honestly be declared complete before the migrations that depend on their architectural direction.

PLAN-003 now separates:

- architecture ratchet foundation → concrete seam migrations → zero-exception architecture closure;
- port convention/inventory foundation → concrete capability ports → generic FileStorage cleanup → port-requirement closure.

This removes the false implication that a parent architecture REQ must already be fully true before the work needed to make it true can start.

### 3. PLAN-004 now follows the frozen “one workflow at a time” migration rule

The draft represented `REQ-ARC-002` as one large task spanning submission, cancellation, history, search, rename, summary, export, retention and delivery policy.

That contradicted PLAN-004's reversible, workflow-by-workflow migration strategy.

The corrected decomposition adds explicit extraction tasks for admission/reprocess, history, search, transcript derivatives and operational commands. `TASK-P04-014` is the single closure owner for the thin-Telegram invariant.

### 4. Generic/dead-abstraction cleanup no longer has two owners

The draft PLAN-003 cleanup could remove generic `FileStorage` **and** unrelated speculative/empty abstraction surfaces, while `REQ-NFR-005` in PLAN-004 also owned the latter.

PLAN-003 is now limited to generic `FileStorage` and its wiring after replacement/no-consumer evidence. Broader empty/speculative-package cleanup remains with `TASK-P04-016`.

### 5. NFR closure tasks no longer duplicate behavior fixes

Compatibility, reliability and refactor-quality requirements are cross-cutting. Their tasks are now explicitly marked as assurance owners.

If an assurance criterion fails because a domain/data/workflow owner is wrong, that earlier owner is reopened. The assurance task does not create a second implementation.

### 6. Operational evidence is reusable instead of repeated

The same real backup/restore, restart, systemd, rollback or manual-recovery rehearsal may satisfy several frozen evidence obligations.

The package now names the producing task and all consumers of each evidence record. Readiness aggregation references valid evidence and reruns only when a material change invalidates it.

### 7. Environment-only behavior no longer requires artificial unit-test Red

The task execution rule now follows Constitution II explicitly: host-only acceptance may use a failing preflight/rehearsal criterion as Red evidence. Helper/unit tests do not impersonate host evidence.

## Final coherence result

After correction:

- Constitution/spec/REQ/PLAN semantics changed: **0**;
- frozen REQs with a primary execution owner: **66/66**;
- duplicate primary REQ owners: **0**;
- tasks: **81**;
- support/foundation tasks: **9**;
- plan gates: **6**;
- unknown task dependencies: **0**;
- dependency cycles: **0**;
- same-plan forward dependencies: **0**;
- cross-plan dependency bypasses: **0**;
- known semantic responsibility overlaps without an explicit handoff: **0**;
- frozen-out future features introduced: **0**.

## Approval conclusion

`005-tasks` is coherent with the approved documentation and internally integrated after the corrections above. It is suitable for promotion to v1.0.0 / Approved / Frozen and may authorize TDD implementation in dependency order.
