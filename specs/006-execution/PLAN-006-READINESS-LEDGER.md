# PLAN-006 readiness ledger

Status: **Verified / closed - TASK-P06-010 readiness evidence accepted**
Owner task: **TASK-P06-010**
Primary requirement: **REQ-OPS-007**
Operational evidence baseline: **`ed3985b7e9337cbd05a3dec896c29845865fbda2`**
Recorded: **2026-08-18**
Target environment: **private / single-operator Linux host**

This is a non-normative execution ledger. It aggregates valid evidence from the
frozen PLAN-006 owner tasks without redefining requirements or claiming that
helper/unit tests substitute for operational rehearsals.

Raw host/staging records remain private under `~/Downloads`. Only sanitized
summary facts and local evidence locators are versioned here. Reusable
credentials, environment-file values, authentication cookies, transcript
content, provider payloads and private numeric identifiers are intentionally
excluded.

## Evidence classification

| Owner | Requirement | Evidence mode | Decision |
|---|---|---|---|
| `TASK-P06-001` | `REQ-NFR-004` | implemented/tested assurance | PASS |
| `TASK-P06-003` | `REQ-OPS-001` | empirically rehearsed | PASS |
| `TASK-P06-004` | `REQ-OPS-002` | implemented/tested behavior | PASS |
| `TASK-P06-005` | `REQ-OPS-003` | empirically rehearsed | PASS |
| `TASK-P06-006` | `REQ-OPS-004` (+ `REQ-DATA-009`) | empirically rehearsed | PASS |
| `TASK-P06-007` | `REQ-OPS-005` | empirically rehearsed, reused after materiality review | PASS |
| `TASK-P06-008` | `REQ-OPS-006` | empirically rehearsed, reused after materiality review | PASS |

The distinction above is intentional. `TASK-P06-001` and `TASK-P06-004` are not
promoted to host-rehearsal evidence merely because their tests pass. The real
operational proof required by `REQ-OPS-007` is supplied by the restart,
systemd, backup/restore, rollback and manual-recovery records below.

## E-001 — Supported runtime and environment-gated lineage

- Owner task: `TASK-P06-001`
- Requirement: `REQ-NFR-004`
- Revision: exact worktree later committed as `ed3985b7e9337cbd05a3dec896c29845865fbda2`
- Environment class: supported local Linux/Python environment plus classified integration suite
- Objective: preserve explicit lineage for the frozen 46 environment-gated contracts and execute the currently valid set without false-pass classification
- Actions: reconcile historical inventory; classify replacements/retirements; run the current integration suite
- Expected: all 46 historical contracts have an explicit disposition; no `MISSING`; the current executable inventory is 35
- Observed: `30 PRESERVED + 4 REPLACED_BY_DECOMPOSITION + 1 REPLACED_BY_PORTABILITY_CONTRACT + 11 RETIRED_WITH_ABSTRACTION = 46`; `MISSING = 0`; current integration execution `35 passed`
- Decision: **PASS**
- Evidence mode: `implemented/tested assurance`
- Evidence source: `specs/006-execution/PLAN-006-ENVIRONMENT-GATED-LINEAGE.md`
- Materiality / reuse: the later P06-005 evidence-persistence fix changed only the preflight report writer/tests and did not alter the integration lineage or the classified product contracts

## E-003 — Startup/restart reconciliation

- Owner task: `TASK-P06-003`
- Requirement: `REQ-OPS-001`
- Revision: `ed3985b7e9337cbd05a3dec896c29845865fbda2`
- Environment class: private-host isolated SQLite staging with a fresh Python-process boundary
- Objective: empirically exercise source-valid pending requeue and deterministic reconciliation of interrupted active/delivery states without mutating production data
- Actions: process A created 10 durable synthetic pre-restart states and exited; process B opened the same SQLite in a fresh interpreter and invoked the production `StartupRecoveryService`; persisted results were reopened and checked
- Expected: valid pending work remains pending and is selected for requeue; invalid pending and interrupted active work become `failed`; interrupted `delivering` becomes `delivery_failed`; no checkpoint resume is claimed
- Observed: valid YouTube and Telegram-audio pending cases were selected for requeue; invalid pending became `failed`; `acquiring`, `converting`, `transcribing`, `diarizing` and `rendering` became `failed`; `delivering` became `delivery_failed`; no interrupted active state survived
- Decision: **PASS**
- Evidence mode: `empirically rehearsed`
- Evidence source: `~/Downloads/p06-003-restart-reconciliation-20260818T210053Z/restart-reconciliation-20260818T210053Z.json`
- Materiality / reuse: captured directly on the operational evidence baseline; no reuse inference is required

## E-004 — Automatic completed-Job retention

- Owner task: `TASK-P06-004`
- Requirement: `REQ-OPS-002`
- Revision: `ed3985b7e9337cbd05a3dec896c29845865fbda2`
- Environment class: focused local application/Telegram-adapter test execution; production service observed but not mutated
- Objective: verify deterministic retention execution, canonical/reference truth and failure isolation
- Actions: run the retention-policy suite plus automatic post-delivery invocation and retention-failure isolation tests
- Expected: configured FIFO retention is deterministic; canonical snapshot/Markdown survive; removed volatile references become truthful; retention failure is recorded without changing a successful `completed` outcome
- Observed: `14 passed`; service remained active; repository remained clean
- Decision: **PASS**
- Evidence mode: `implemented/tested behavior`
- Evidence source: `~/Downloads/p06-004-retention-20260818T210723Z/p06-004-retention-gate-20260818T210723Z.txt`
- Materiality / reuse: captured directly on the operational evidence baseline; this record is deliberately not classified as a host rehearsal because the frozen P06-004 completion evidence is test-based

## E-005 — Private-host systemd lifecycle and protected configuration

- Owner task: `TASK-P06-005`
- Requirement: `REQ-OPS-003`
- Revision: lifecycle smoke at `02eb0bc63b6ecb860530031db1ef1a2b2a03e38d`; final privileged preflight on the exact two-file worktree later committed as `ed3985b7e9337cbd05a3dec896c29845865fbda2`
- Environment class: real private Linux host using the installed `yt-transcriber-bot` systemd service
- Objective: prove supported host prerequisites, least-privilege service lifecycle, protected secret configuration and sanitized operational evidence
- Actions: exercise service status/stop/start/restart/status and sanitized journal collection; run privileged preflight with explicit runtime PATH; validate persisted JSON, file modes, environment-file ownership/mode and service state; validate Telegram `/healthcheck` and `/status` after lifecycle exercise
- Expected: unprivileged configured service account; protected root-owned environment file; start/restart healthy; sanitized evidence; prerequisites present; evidence persistence must not weaken shared directory permissions
- Observed: lifecycle smoke passed; final preflight RC `0`; persisted JSON parsed and reported `passed=true`; report mode `0600`; evidence directory `0700`; environment file `root:root 0600`; `/tmp` remained `1777 root:root`; service remained active; Telegram health/status checks passed
- Decision: **PASS**
- Evidence mode: `empirically rehearsed`
- Evidence source: `~/Downloads/p06-005-systemd-rehearsal-20260818T193329Z/systemd-smoke-20260818T193329Z.md`; `~/Downloads/p06-005-final-preflight-20260818T203056Z/systemd-host-preflight-20260818T203056Z.json`
- Materiality / reuse: the only closure change after the lifecycle smoke was the P06-005 preflight evidence-writer hardening (valid JSON newline and safe parent permissions); it did not change the systemd unit, service runtime, startup path or application behavior, and the corrected preflight itself was rerun on the exact worktree later committed as the operational baseline

## E-006 — Credential-free backup and validated restore

- Owner task: `TASK-P06-006`
- Requirement: `REQ-OPS-004` (also real-evidence support for `REQ-DATA-009`)
- Revision: `ed3985b7e9337cbd05a3dec896c29845865fbda2`
- Environment class: real private-host backup plus isolated restore staging
- Objective: prove that the standard backup is consistency-preserving, credential-free and sufficient to validate durable database/canonical-artifact relationships after restore
- Actions: create controlled standard backup; verify excluded secret/cookie classes; restore into isolated staging; open restored SQLite and validate integrity/history/canonical relationships; perform post-restore `/healthcheck`, `/status` and `/list`
- Expected: protected consistent backup; no `.env`, systemd secret environment file or authentication cookies; isolated restore succeeds; database/history/canonical relationships validate; normal operator checks work afterward
- Observed: backup/restore procedure passed; SQLite opened and integrity validation passed; 13 Jobs were present in restored history; 8 canonical references validated (1 structured and 7 legacy Markdown); no reusable credentials/cookies were copied; Telegram health/status/list responded normally after the procedure
- Decision: **PASS**
- Evidence mode: `empirically rehearsed`
- Evidence source: `~/Downloads/p06-006-backup-20260818T203807Z/standard-backup-20260818T203807Z.md`; `~/Downloads/p06-006-restore-evidence-20260818T204039Z/credential-free-restore-staging-20260818T204039Z.md`
- Materiality / reuse: captured directly on the operational evidence baseline; no reuse inference is required

## E-007 — Versioned upgrade and rollback

- Owner task: `TASK-P06-007`
- Requirement: `REQ-OPS-005`
- Revision: rehearsal source revision `33af49fbdb94bfd7c5c98c25f63ac9d2147c50de`; applicability reviewed through operational baseline `ed3985b7e9337cbd05a3dec896c29845865fbda2`
- Environment class: private host/staging rollback rehearsal with isolated durable-data validation
- Objective: prove versioned rollback with recorded revision, pre-change backup and compatible persisted data without silent destructive migration
- Actions: run upgrade/rollback preflight; exercise rollback code revision; validate backup restore in isolated staging; validate SQLite/database/canonical references; restore the intended production branch/revision
- Expected: code rollback is exercised; durable data remains compatible or follows the approved restore path; post-operation state is explicit and recoverable
- Observed: rehearsal RC `0`; `rollback_code_revision_exercised=yes`; isolated backup restore validated; SQLite integrity `ok`; `jobs` table opened; 8 canonical Job references validated; production branch/revision restored as recorded by the rehearsal
- Decision: **PASS**
- Evidence mode: `empirically rehearsed`
- Evidence source: `~/Downloads/p06-007-preflight/upgrade-rollback-preflight-20260818T180319Z.json`; `~/Downloads/p06-007-rehearsal-clean/upgrade-rollback-rehearsal-20260818T180332Z.md`
- Materiality / reuse: later revisions added the independent P06-008 recovery workflow, P06-009 interface/documentation conformance and the P06-005 preflight evidence-writer fix; they did not change `scripts/ops/upgrade_rollback_rehearsal.py`, persisted schema/migrations, standard backup contract, supported runtime or dependency set. The current P06-006 restore rehearsal additionally reconfirmed durable-data compatibility on `ed3985b...`

## E-008 — Manual artifact recovery after delivery failure

- Owner task: `TASK-P06-008`
- Requirement: `REQ-OPS-006`
- Revision: rehearsal source revision `595ae9d8afc65dd2fdbdb5c6d3d994b963329de0`; applicability reviewed through operational baseline `ed3985b7e9337cbd05a3dec896c29845865fbda2`
- Environment class: isolated private staging recovery rehearsal
- Objective: prove truthful local-artifact recovery for `delivery_failed` without implicit resend, Job reopen or recomputation
- Actions: rehearse recoverable preserved artifact, missing-artifact refusal and terminal-state preservation in isolated staging
- Expected: available protected artifact can be copied manually; absent/purged artifact is reported unavailable; Job remains terminal; no resend/reopen/recompute is triggered
- Observed: recovered copy was byte-identical and mode `0600`; `delivery_failed` remained terminal; missing artifact was refused as unavailable; `implicit_resend=false`, `job_reopened=false`, `recomputation_triggered=false`; production database/service were not modified
- Decision: **PASS**
- Evidence mode: `empirically rehearsed`
- Evidence source: `~/Downloads/p06-008-rehearsal-20260818T185129Z/p06-008-rehearsal.md`
- Materiality / reuse: revisions after the rehearsal changed P06-009 documentation/interface conformance and P06-005 preflight evidence persistence only; the manual-recovery helper/service contract was not changed, so the prior empirical record remains valid

## REQ-OPS-007 acceptance review

- AC-01 — **PASS**: every ledger record above includes revision, environment class, objective, actions, expected, observed and decision.
- AC-02 — **PASS**: P06-003/P06-004/P06-006 were captured directly on `ed3985b...`; P06-005 final preflight used the exact worktree later committed as that revision; older P06-007/P06-008 rehearsals have explicit materiality/reuse justifications.
- AC-03 — **PASS**: this versioned ledger contains no reusable credential values, cookies, transcript/provider payloads or private numeric identifiers; raw records stay under private `~/Downloads`.
- AC-04 — **PASS**: the evidence classification explicitly separates implemented/tested assurance/behavior from empirically rehearsed operation.

## P06-010 decision

`TASK-P06-010` is **CLOSED**. Its readiness-ledger conformance gate passed and the
record was published before the final PLAN-006 exit gate. No failed owner criterion
was found and no product repair belonged in this aggregation task.

## P06-011 exit-gate consumption

`TASK-P06-011` consumed this ledger at published baseline
`318d90dda0ead178c5df30b899fb4fea4430fc0d`. The final read-only Stage A gate
passed Ruff, global format check, mypy, default pytest, full conformance, all 35
current integration tests, environment-gated lineage validation, security scans,
compile, the official fake benchmark, pre-commit and repository/service invariants.

Decision: **GREEN / PASS**.

Sanitized summary:
`~/Downloads/p06-011-exit-gate-20260818T231226Z/p06-011-exit-gate-summary-20260818T231226Z.txt`.

The Stage B closure-document changes are non-material to the operational evidence
aggregated above and therefore do not require repetition of the host/staging rehearsals.
