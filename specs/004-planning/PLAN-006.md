# PLAN-006 — Deployment, backup, documentation and operational-evidence closure

Version: **1.0.0**
Status: **Approved / Frozen**
Derived from: **003-atomic-requirements v1.0.0**
Prerequisite plans: **PLAN-005** *(earlier gates inherited transitively)*
Approved: **2026-08-15**

## Goal

Close the Architecture & Specification Baseline with supported-runtime evidence, corrected current operator documentation, credential-free backup/restore, systemd/rollback/recovery rehearsals, interface/documentation conformance and an explicit readiness record.

## Primary requirement scope

- `REQ-DATA-009` — Credential-free standard backup and restore integrity
- `REQ-NFR-004` — Supported runtime portability and environment-gated evidence
- `REQ-FUNC-012` — Command, help and documentation conformance
- `REQ-OPS-001` — Source-valid startup and restart reconciliation
- `REQ-OPS-002` — Automatic completed-Job retention execution
- `REQ-OPS-003` — Private host installation and systemd service lifecycle
- `REQ-OPS-004` — Credential-free backup and validated restore procedure
- `REQ-OPS-005` — Versioned upgrade and rollback procedure
- `REQ-OPS-006` — Manual artifact recovery after delivery failure
- `REQ-OPS-007` — Reproducible host/staging readiness evidence

## Implementation approach

1. Reconcile current README/manual/runbook/roadmap/readiness documents with approved specifications while leaving historical gate reports and patch notes historical.
2. Correct the standard backup set/procedure so `.env`, systemd secret env and authentication cookies are reprovisioned rather than copied into the standard backup.
3. Validate install/runtime prerequisites and the classified environment-gated test set on supported environments.
4. Exercise startup reconciliation, automatic retention, systemd start/stop/restart, backup/restore, upgrade/rollback and manual `delivery_failed` recovery on authorized host/staging.
5. Record sanitized evidence with revision, environment, objective, expected result, observed result and pass/fail information.
6. Update product naming, command/help/manual conformance, production-readiness ledger and roadmap drift only against behavior that passed prior plan gates.
7. Perform final specification↔implementation↔tests↔current-doc conformance review before declaring the milestone stabilized.

## Ownership boundary and handoff

PLAN-006 owns **host/deployment evidence and current documentation convergence**. It must not redesign domain/application architecture during rehearsal. If an operational rehearsal exposes a defect, the change returns to the owning earlier requirement/task and is revalidated through the dependency chain before closure.

Historical evidence remains historical; only current normative/operator documentation is converged.

## Migration and compatibility constraints

- Do not count helper-script unit tests as host rehearsal evidence.
- Do not paste secret-bearing or transcript-bearing raw logs into collaboration artifacts.
- Do not rewrite old gate reports to make them appear compliant with later specifications.
- Do not include reusable credentials/cookies in the standard backup merely for rollback convenience.

## Exit gate

- All required host/staging rehearsals have recorded sanitized evidence.
- Backup/restore excludes reusable credentials and validates database/canonical relationships after restore.
- systemd/upgrade/rollback/recovery procedures pass on the intended closure revision.
- README/manual/help/roadmap/current readiness documentation conforms to frozen specifications.
- The 46 classified integration tests have an explicit executed/not-executed result appropriate to the supported environment and no required evidence is silently omitted.
- Final conformance review finds no unresolved requirement or documentation drift blocking the baseline milestone.
- The remediation milestone can be declared stabilized before new product functionality resumes.

## Not tasks

The numbered approach above defines migration order and design constraints, not a task checklist. Concrete files, red tests, implementation increments, commits and task ownership are defined in `../005-tasks/`.
