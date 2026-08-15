# PLAN-006 Tasks — Deployment, backup, documentation and operational-evidence closure

Version: **1.0.0**
Status: **Approved / Frozen**
Derived from: **004-planning v1.0.0 (Approved / Frozen)**

## Execution rule

PLAN-006 distinguishes implementation/procedure ownership from **evidence aggregation**. A real rehearsal may satisfy multiple frozen evidence obligations when it exercises the same contract on the same closure revision; reference the same sanitized record instead of rerunning identical operations. Host-only acceptance uses preflight/rehearsal failure as Red evidence.

## TASK-P06-001 — Supported runtime portability and environment-gated evidence

**Primary REQ:** `REQ-NFR-004`
**Task role:** **assurance owner**
**Dependencies:** `TASK-P05-017`

### Implementation intent

Supported Python/Linux/runtime expectations SHALL be explicit and reproducible, and tests requiring host-specific capabilities SHALL be clearly classified, gated and reported rather than silently treated as passed.

**Current brownfield focus:** No specific brownfield defect is singled out; preserve approved behavior while establishing the required contract.

**Likely touchpoints:** Supported Python/Linux/runtime matrix, integration marker classification and environment-specific evidence.

**Integration note:** Environment-gated test execution/classification may be referenced by TASK-P06-010 and the plan gate; do not rerun identical evidence solely for bookkeeping.

### Red

Create or strengthen the lowest useful tests that express the frozen acceptance boundary:

- AC-01: Supported Python versions match project metadata and CI configuration.
- AC-02: Supported Linux/system dependencies are documented and can be checked through health/preflight evidence.
- AC-03: Every currently inventoried environment-gated contract test retains its evidence role or has an explicit replacement before removal.
- AC-04: An unavailable environment-gated capability produces a visible skip/unavailability reason rather than a false pass.

If all acceptance criteria are already satisfied, record characterization evidence instead of manufacturing an artificial failing test. For host-only or environment-only criteria, a failing preflight/rehearsal criterion is valid Red evidence; do not fabricate a unit-test substitute.

### Green

Implement the minimum coherent change required to satisfy the failing acceptance evidence while preserving all upstream frozen behavior and the current plan ownership boundary.

### Refactor / convergence

Remove temporary duplication introduced by the migration, keep one owner for the policy/capability, and run relevant architecture/contract/conformance checks before considering the task complete.

### Completion evidence

- pyproject/CI/documentation conformance tests
- inventory mapping for environment-gated tests
- host-specific test reports

Also record the quality gates actually run and any environment-gated evidence deferred to PLAN-006.

## TASK-P06-002 — Credential-free standard backup and restore integrity

**Primary REQ:** `REQ-DATA-009`
**Task role:** **data-contract owner**
**Dependencies:** `TASK-P05-017`

### Implementation intent

The standard operational backup SHALL capture the minimum durable data required to restore approved history and artifact relationships while excluding reusable provider credentials, secret-bearing environment files and authentication cookies.

**Current brownfield focus:** Current runbook copies systemd env and `.env` into the standard backup and must converge with the approved security specification.

**Likely touchpoints:** Standard backup dataset/relationships and explicit exclusion of reusable credentials/cookies.

**Integration note:** Define/verify the standard backup data contract. A real backup/restore rehearsal captured by TASK-P06-006 on the same closure revision may satisfy this REQ's real-evidence requirement; do not execute a duplicate rehearsal.

### Red

Create or strengthen the lowest useful tests that express the frozen acceptance boundary:

- AC-01: The documented standard backup set explicitly lists included and excluded data classes.
- AC-02: SQLite backup is obtained through a consistency-preserving mechanism.
- AC-03: Restore preserves canonical transcript links, history and database integrity.
- AC-04: Reusable credentials, secret-bearing env files and authentication cookies are reprovisioned separately rather than copied into the standard backup.

If all acceptance criteria are already satisfied, record characterization evidence instead of manufacturing an artificial failing test. For host-only or environment-only criteria, a failing preflight/rehearsal criterion is valid Red evidence; do not fabricate a unit-test substitute.

### Green

Implement the minimum coherent change required to satisfy the failing acceptance evidence while preserving all upstream frozen behavior and the current plan ownership boundary.

### Refactor / convergence

Remove temporary duplication introduced by the migration, keep one owner for the policy/capability, and run relevant architecture/contract/conformance checks before considering the task complete.

### Completion evidence

- backup-helper tests
- real backup/restore rehearsal
- post-restore health/status/list evidence

Also record the quality gates actually run and any environment-gated evidence deferred to PLAN-006.

## TASK-P06-003 — Source-valid startup and restart reconciliation

**Primary REQ:** `REQ-OPS-001`
**Task role:** **operational owner**
**Dependencies:** `TASK-P05-017`

### Implementation intent

On startup the system SHALL deterministically requeue only source-valid pending work and reconcile interrupted active/delivery states to the approved terminal outcomes without claiming checkpoint resume.

**Current brownfield focus:** No specific brownfield defect is singled out; preserve approved behavior while establishing the required contract.

**Likely touchpoints:** Real/startup file-backed pending/active/delivering reconciliation and notifications.

**Integration note:** Its restart rehearsal record is consumed by TASK-P06-010 readiness evidence; rerun only after a material change invalidates it.

### Red

Create or strengthen the lowest useful tests that express the frozen acceptance boundary:

- AC-01: Pending work is requeued only when required source-specific acquisition context and delivery/request context remain usable.
- AC-02: Legacy or incomplete pending work without recoverable payload becomes `failed`.
- AC-03: Interrupted `acquiring`, `converting`, `transcribing`, `diarizing` or `rendering` work becomes `failed`.
- AC-04: Interrupted `delivering` work becomes `delivery_failed`.
- AC-05: No mid-stage checkpoint resume is advertised or inferred.

If all acceptance criteria are already satisfied, record characterization evidence instead of manufacturing an artificial failing test. For host-only or environment-only criteria, a failing preflight/rehearsal criterion is valid Red evidence; do not fabricate a unit-test substitute.

### Green

Implement the minimum coherent change required to satisfy the failing acceptance evidence while preserving all upstream frozen behavior and the current plan ownership boundary.

### Refactor / convergence

Remove temporary duplication introduced by the migration, keep one owner for the policy/capability, and run relevant architecture/contract/conformance checks before considering the task complete.

### Completion evidence

- startup-recovery unit tests
- SQLite integration recovery tests
- restart rehearsal evidence

Also record the quality gates actually run and any environment-gated evidence deferred to PLAN-006.

## TASK-P06-004 — Automatic completed-Job retention execution

**Primary REQ:** `REQ-OPS-002`
**Task role:** **operational owner**
**Dependencies:** `TASK-P05-017`

### Implementation intent

The system SHALL apply configured automatic retention to eligible volatile artifacts of completed Jobs without removing canonical transcript evidence or leaving false durable availability references.

**Current brownfield focus:** No specific brownfield defect is singled out; preserve approved behavior while establishing the required contract.

**Likely touchpoints:** Automatic retention invocation after completion and canonical/reference integrity.

### Red

Create or strengthen the lowest useful tests that express the frozen acceptance boundary:

- AC-01: Configured retention count/policy is enforced deterministically.
- AC-02: Canonical structured snapshot and Markdown required by approved history, rename and export behavior are preserved.
- AC-03: Removed volatile-media/log references are cleared or marked unavailable coherently.
- AC-04: Retention failure is sanitized/recorded and does not retroactively change a successfully completed primary-delivery outcome.

If all acceptance criteria are already satisfied, record characterization evidence instead of manufacturing an artificial failing test. For host-only or environment-only criteria, a failing preflight/rehearsal criterion is valid Red evidence; do not fabricate a unit-test substitute.

### Green

Implement the minimum coherent change required to satisfy the failing acceptance evidence while preserving all upstream frozen behavior and the current plan ownership boundary.

### Refactor / convergence

Remove temporary duplication introduced by the migration, keep one owner for the policy/capability, and run relevant architecture/contract/conformance checks before considering the task complete.

### Completion evidence

- retention execution tests
- reference-truth tests
- failure-isolation tests

Also record the quality gates actually run and any environment-gated evidence deferred to PLAN-006.

## TASK-P06-005 — Private host installation and systemd service lifecycle

**Primary REQ:** `REQ-OPS-003`
**Task role:** **operational owner**
**Dependencies:** `TASK-P05-017`, `TASK-P06-001`

### Implementation intent

The deployment baseline SHALL document and verify supported host prerequisites plus least-privilege systemd start/stop/restart/log operation with protected secret configuration outside tracked repository content.

**Current brownfield focus:** No specific brownfield defect is singled out; preserve approved behavior while establishing the required contract.

**Likely touchpoints:** Install prerequisites, systemd unit, least-privilege runtime, start/stop/restart/log operations and secret provisioning.

**Integration note:** Its systemd/permission rehearsal record is consumed by TASK-P06-010; evidence reuse is expected on the same closure revision.

### Red

Create or strengthen the lowest useful tests that express the frozen acceptance boundary:

- AC-01: The service runs under an unprivileged configured account; any root/privilege exception requires an explicit constitutional/specification exception rather than an undocumented deployment shortcut.
- AC-02: The systemd secret/environment source has restrictive owner/mode verified by host preflight or rehearsal.
- AC-03: Start and restart are followed by the approved health/status validation.
- AC-04: Journal/evidence output is sanitized before being moved to collaboration surfaces.
- AC-05: Install prerequisites match approved Python/Linux/ffmpeg/runtime expectations.

If all acceptance criteria are already satisfied, record characterization evidence instead of manufacturing an artificial failing test. For host-only or environment-only criteria, a failing preflight/rehearsal criterion is valid Red evidence; do not fabricate a unit-test substitute.

### Green

Implement the minimum coherent change required to satisfy the failing acceptance evidence while preserving all upstream frozen behavior and the current plan ownership boundary.

### Refactor / convergence

Remove temporary duplication introduced by the migration, keep one owner for the policy/capability, and run relevant architecture/contract/conformance checks before considering the task complete.

### Completion evidence

- deployment/preflight tests
- systemd host rehearsal evidence
- permission evidence

Also record the quality gates actually run and any environment-gated evidence deferred to PLAN-006.

## TASK-P06-006 — Credential-free backup and validated restore procedure

**Primary REQ:** `REQ-OPS-004`
**Task role:** **operational procedure owner**
**Dependencies:** `TASK-P05-017`, `TASK-P06-002`, `TASK-P06-005`

### Implementation intent

The operator SHALL have a repeatable backup/restore procedure for the approved standard backup set that excludes reusable credentials/cookies and validates restored database/canonical-artifact relationships before resuming normal operation.

**Current brownfield focus:** No specific brownfield defect is singled out; preserve approved behavior while establishing the required contract.

**Likely touchpoints:** Cold/controlled backup+restore procedure and restored database/canonical relationship validation.

**Integration note:** This task owns the operator procedure and real backup/restore rehearsal. The resulting evidence also satisfies compatible evidence requirements in TASK-P06-002 and is aggregated by TASK-P06-010.

### Red

Create or strengthen the lowest useful tests that express the frozen acceptance boundary:

- AC-01: Backup uses a consistency-preserving SQLite copy and protected storage.
- AC-02: Standard procedure does not copy `.env`, the systemd secret environment file or authentication cookies.
- AC-03: Restore occurs with the service stopped or in isolated staging.
- AC-04: Post-restore database-open plus approved health/status/history checks are captured.

If all acceptance criteria are already satisfied, record characterization evidence instead of manufacturing an artificial failing test. For host-only or environment-only criteria, a failing preflight/rehearsal criterion is valid Red evidence; do not fabricate a unit-test substitute.

### Green

Implement the minimum coherent change required to satisfy the failing acceptance evidence while preserving all upstream frozen behavior and the current plan ownership boundary.

### Refactor / convergence

Remove temporary duplication introduced by the migration, keep one owner for the policy/capability, and run relevant architecture/contract/conformance checks before considering the task complete.

### Completion evidence

- backup-helper tests
- real backup/restore rehearsal evidence

Also record the quality gates actually run and any environment-gated evidence deferred to PLAN-006.

## TASK-P06-007 — Versioned upgrade and rollback procedure

**Primary REQ:** `REQ-OPS-005`
**Task role:** **operational procedure owner**
**Dependencies:** `TASK-P05-017`, `TASK-P06-005`, `TASK-P06-006`

### Implementation intent

The operator SHALL be able to upgrade and roll back the application with recorded Git revision, compatible persisted data, pre-change backup and post-change validation, without silent destructive migration.

**Current brownfield focus:** No specific brownfield defect is singled out; preserve approved behavior while establishing the required contract.

**Likely touchpoints:** Versioned pre-upgrade backup, migration compatibility, rollback and post-rollback validation.

**Integration note:** Its rollback rehearsal record is aggregated by TASK-P06-010 rather than repeated there.

### Red

Create or strengthen the lowest useful tests that express the frozen acceptance boundary:

- AC-01: Pre-upgrade revision and backup are recorded.
- AC-02: Migration/compatibility checks pass before the production upgrade proceeds.
- AC-03: Rollback restores the prior code revision and, when required by a migration, compatible prior data through the approved recovery path.
- AC-04: Health/status/journal validation is recorded after upgrade and rollback.

If all acceptance criteria are already satisfied, record characterization evidence instead of manufacturing an artificial failing test. For host-only or environment-only criteria, a failing preflight/rehearsal criterion is valid Red evidence; do not fabricate a unit-test substitute.

### Green

Implement the minimum coherent change required to satisfy the failing acceptance evidence while preserving all upstream frozen behavior and the current plan ownership boundary.

### Refactor / convergence

Remove temporary duplication introduced by the migration, keep one owner for the policy/capability, and run relevant architecture/contract/conformance checks before considering the task complete.

### Completion evidence

- upgrade/rollback helper tests
- real host/staging rollback rehearsal

Also record the quality gates actually run and any environment-gated evidence deferred to PLAN-006.

## TASK-P06-008 — Manual artifact recovery after delivery failure

**Primary REQ:** `REQ-OPS-006`
**Task role:** **operational procedure owner**
**Dependencies:** `TASK-P05-017`

### Implementation intent

For `delivery_failed` or interrupted-delivery scenarios, the operator SHALL be able to determine whether preserved local artifacts actually exist and recover them manually without reopening the terminal Job or leaking secrets/private payloads through diagnostics.

**Current brownfield focus:** No specific brownfield defect is singled out; preserve approved behavior while establishing the required contract.

**Likely touchpoints:** `delivery_failed`, `/lasterror`, preserved local artifact checks and manual recovery procedure.

**Integration note:** Its delivery-failed/manual-recovery rehearsal record is aggregated by TASK-P06-010 rather than repeated there.

### Red

Create or strengthen the lowest useful tests that express the frozen acceptance boundary:

- AC-01: `/lasterror` or equivalent operational data reflects actual artifact availability.
- AC-02: Recovery uses local protected artifacts and documented operator steps.
- AC-03: No implicit resend or Job reopen occurs.
- AC-04: A missing or retention-purged artifact is reported unavailable rather than recoverable.

If all acceptance criteria are already satisfied, record characterization evidence instead of manufacturing an artificial failing test. For host-only or environment-only criteria, a failing preflight/rehearsal criterion is valid Red evidence; do not fabricate a unit-test substitute.

### Green

Implement the minimum coherent change required to satisfy the failing acceptance evidence while preserving all upstream frozen behavior and the current plan ownership boundary.

### Refactor / convergence

Remove temporary duplication introduced by the migration, keep one owner for the policy/capability, and run relevant architecture/contract/conformance checks before considering the task complete.

### Completion evidence

- manual-recovery workflow tests
- delivery-failed host/staging rehearsal

Also record the quality gates actually run and any environment-gated evidence deferred to PLAN-006.

## TASK-P06-009 — Command, help and documentation conformance

**Primary REQ:** `REQ-FUNC-012`
**Task role:** **conformance owner**
**Dependencies:** `TASK-P05-017`

### Implementation intent

Registered commands, aliases, help/manual text, product naming and current/future documentation SHALL conform to the approved baseline without claiming unimplemented features or preserving obsolete YouTube-only product identity.

**Current brownfield focus:** No specific brownfield defect is singled out; preserve approved behavior while establishing the required contract.

**Likely touchpoints:** Command registration, aliases, HELP_TEXT, current manuals/README/product naming and future-roadmap claims.

**Integration note:** Converge only current normative/operator documentation; historical gate reports and patch notes remain historical.

### Red

Create or strengthen the lowest useful tests that express the frozen acceptance boundary:

- AC-01: Command registration matches the documented current command set and aliases.
- AC-02: Help/manual do not advertise future semantic search, translation or other frozen-out functionality.
- AC-03: Roadmap does not list already-shipped CI/current capabilities as future work.
- AC-04: Package/README description reflects the current YouTube-plus-Telegram-media product scope.
- AC-05: Historical gate reports remain historical rather than being rewritten as current normative specifications.

If all acceptance criteria are already satisfied, record characterization evidence instead of manufacturing an artificial failing test. For host-only or environment-only criteria, a failing preflight/rehearsal criterion is valid Red evidence; do not fabricate a unit-test substitute.

### Green

Implement the minimum coherent change required to satisfy the failing acceptance evidence while preserving all upstream frozen behavior and the current plan ownership boundary.

### Refactor / convergence

Remove temporary duplication introduced by the migration, keep one owner for the policy/capability, and run relevant architecture/contract/conformance checks before considering the task complete.

### Completion evidence

- command-registration tests
- documentation-conformance tests
- roadmap/current-capability cross-check

Also record the quality gates actually run and any environment-gated evidence deferred to PLAN-006.

## TASK-P06-010 — Reproducible host/staging readiness evidence

**Primary REQ:** `REQ-OPS-007`
**Task role:** **evidence aggregator / owner**
**Dependencies:** `TASK-P05-017`, `TASK-P06-003`, `TASK-P06-004`, `TASK-P06-005`, `TASK-P06-006`, `TASK-P06-007`, `TASK-P06-008`

### Implementation intent

Private-production readiness SHALL require sanitized reproducible host/staging evidence for systemd lifecycle, backup/restore, rollback, restart reconciliation and delivery-failed/manual recovery; helper-script tests alone SHALL not count as proof.

**Current brownfield focus:** No specific brownfield defect is singled out; preserve approved behavior while establishing the required contract.

**Likely touchpoints:** Sanitized host/staging evidence records for all required operational rehearsals.

**Integration note:** Aggregate valid evidence from TASK-P06-001/003/005/006/007/008. Do not rerun a rehearsal merely to duplicate evidence; rerun only when revision/environment changes materially invalidate prior evidence.

### Red

Create or strengthen the lowest useful tests that express the frozen acceptance boundary:

- AC-01: Each evidence record identifies revision, environment class, objective, actions, expected result, observed result and pass/fail decision.
- AC-02: Required real rehearsals run on the revision intended for closure or are explicitly repeated after a material change that invalidates prior evidence.
- AC-03: Evidence contains no reusable credentials or private transcript/provider payloads.
- AC-04: Readiness ledger distinguishes implemented/tested behavior from empirically rehearsed operation.

If all acceptance criteria are already satisfied, record characterization evidence instead of manufacturing an artificial failing test. For host-only or environment-only criteria, a failing preflight/rehearsal criterion is valid Red evidence; do not fabricate a unit-test substitute.

### Green

Assemble the readiness ledger from valid sanitized evidence produced by the owning operational tasks. Do not implement or repair product behavior here. If required evidence is missing or a rehearsal fails, reopen the owning task. Repeat a rehearsal only when the closure revision/environment materially changed or the prior record is incomplete/invalid.

### Refactor / convergence

Remove temporary duplication introduced by the migration, keep one owner for the policy/capability, and run relevant architecture/contract/conformance checks before considering the task complete.

### Completion evidence

- host/staging rehearsal records
- readiness-ledger conformance review

Also record the quality gates actually run and any environment-gated evidence deferred to PLAN-006.

## TASK-P06-011 — PLAN-006 exit-gate verification

**Primary REQ:** none; plan gate
**Task role:** **plan gate**
**Dependencies:** `TASK-P06-001`, `TASK-P06-002`, `TASK-P06-003`, `TASK-P06-004`, `TASK-P06-005`, `TASK-P06-006`, `TASK-P06-007`, `TASK-P06-008`, `TASK-P06-009`, `TASK-P06-010`

### Scope

Verify that every primary owner, support/foundation task and assurance task in PLAN-006 satisfies the frozen plan exit gate before work in the next plan is treated as implementation-ready. This task does not add product behavior or reimplement a failed criterion.

### Gate evidence

- All required host/staging rehearsals have recorded sanitized evidence.
- Backup/restore excludes reusable credentials and validates database/canonical relationships after restore.
- systemd/upgrade/rollback/recovery procedures pass on the intended closure revision.
- README/manual/help/roadmap/current readiness documentation conforms to frozen specifications.
- The 46 classified integration tests have an explicit executed/not-executed result appropriate to the supported environment and no required evidence is silently omitted.
- Final conformance review finds no unresolved requirement or documentation drift blocking the baseline milestone.
- The remediation milestone can be declared stabilized before new product functionality resumes.

### Completion rule

Record commands/evidence, unresolved environment limitations and any failed criterion. A failed criterion MUST be routed to the task that owns the missing behavior or evidence; the gate itself does not patch around the failure. Shared operational evidence may be referenced rather than rerun when it was captured on the same closure revision and remains valid.
