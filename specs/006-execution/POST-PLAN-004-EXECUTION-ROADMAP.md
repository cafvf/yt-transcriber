# Simplified execution roadmap after PLAN-004

Status: **Active execution view / non-normative — PLAN-004 closed**
Decision date: **2026-08-16**
Activation condition: **only after TASK-P04-017 closes PLAN-004**
Checkpoint when recorded: `43d906911d7ccd4d32ce738f8dffea32ed116244`

This document simplifies **execution tracking and session continuity**. It does not
replace or amend frozen requirements, plans, tasks, owners, dependencies or exit
gates.

## Why this execution view exists

The specification remains intentionally detailed, but daily tracking had accumulated
too many simultaneous levels: requirements, plans, tasks, phases and PLAN-004
review/push subphases. That made it difficult to answer simple project-management
questions such as "where are we?", "what is next?" and "how much remains?".

The remedy is not to rewrite the normative task graph. Instead:

- frozen requirements remain the source of accepted behavior;
- PLAN-004, PLAN-005 and PLAN-006 remain the approved plans;
- `TASK-Pxx-yyy` items remain the authoritative implementation/evidence checklist;
- existing phase definitions remain valid;
- after PLAN-004, ordinary progress reporting uses five larger execution packages.

## Transition rule

PLAN-004 is **not replanned**.

Its remaining execution continues exactly through the already-recorded review/push
boundaries:

1. **Subphase C — TASK-P04-004..013**: derived data, search, summary and operations.
2. **Subphase D — TASK-P04-014..017**: thin Telegram, reliability, convergence and
   PLAN-004 exit gate.

Only after `TASK-P04-017` passes and PLAN-004 is closed does the five-package view
below become the default tracking model.

## Five post-PLAN-004 execution packages

The packages are management/review boundaries. They group approved PLAN-005 and
PLAN-006 work by outcome; they do not become new requirement owners and they do not
override any task dependency.

### Package 1 — Product execution acceptance

**Goal:** prove that the repaired architecture executes the principal product path
correctly under bounded, observable and responsive runtime behavior.

Expected coverage includes the applicable frozen PLAN-005 tasks for:

- bounded resources, waits and cancellation;
- privacy-aware observability;
- Telegram responsiveness;
- supported submission and explicit reprocessing;
- truthful media/subtitle/ASR/diarization processing;
- primary versus derivative delivery outcomes.

**Exit result:** the main processing path is functionally accepted on the repaired
architecture, with the corresponding PLAN-005 task criteria/evidence satisfied.

### Package 2 — Operator workflow acceptance

**Goal:** accept the remaining operator-facing workflows without reintroducing policy
into Telegram or infrastructure.

Expected coverage includes the applicable frozen PLAN-005 tasks for areas such as:

- completed history and textual search;
- rename/merge and transcript-derived operations;
- exports and video derivatives;
- summarization;
- operational commands and other approved operator workflows.

**Exit result:** operator workflows are accepted end to end while preserving the
application ownership established by PLAN-004.

### Package 3 — PLAN-005 convergence and acceptance closure

**Goal:** close all remaining PLAN-005 functional/NFR acceptance obligations and run
the plan exit gate.

This package absorbs whatever frozen PLAN-005 tasks remain after Packages 1 and 2,
including cross-cutting acceptance/convergence work and `TASK-P05-017`.

**Exit result:** every PLAN-005 task is closed or explicitly routed back to its
correct upstream owner; PLAN-005 exit evidence is complete.

### Package 4 — Deployment, persistence resilience and service operations

**Goal:** establish the production-operable baseline before final readiness closure.

Expected coverage includes the applicable frozen PLAN-006 tasks for:

- supported runtime/environment evidence;
- credential-free standard backup and restore integrity;
- source-valid startup/restart reconciliation;
- automatic retention execution;
- private-host installation and systemd lifecycle;
- supporting deployment/restore/rehearsal procedures required by their dependencies.

**Exit result:** installation, durable-data recovery, restart and routine service
operation are reproducible and evidenced on the approved closure revision.

### Package 5 — Production readiness and roadmap closure

**Goal:** aggregate the remaining operational rehearsals/evidence, close PLAN-006 and
finish the current roadmap.

This package absorbs all remaining frozen PLAN-006 tasks after Package 4, including
readiness/evidence aggregation, final documentation/operational closure and the
PLAN-006 exit gate.

**Exit result:** PLAN-006 is closed and the current roadmap has a single evidenced
production-readiness closure point.

## Mapping rule

The package descriptions above are intentionally outcome-based rather than a second
normative task table.

At the start of each package:

1. read the current frozen PLAN task file;
2. enumerate the still-open tasks that contribute to the package outcome;
3. preserve every frozen dependency and owner;
4. execute TDD/characterization at the owning task level;
5. do not declare the package closed until every mapped task is closed or explicitly
   deferred/routed according to its frozen completion rule.

This prevents the simplified view from becoming a competing source of truth.

## Execution cadence after PLAN-004

For each package:

1. implement in small reviewable functional commits;
2. keep task-level tests/characterization and ownership evidence;
3. avoid a full documentation/push ceremony after every individual task unless a
   task boundary materially needs independent publication;
4. run one package-level convergence/full gate after the package contents are green;
5. create one package documentation-closure commit;
6. push the package;
7. verify local `HEAD == origin/main` and a clean worktree.

A second documentation-only commit whose sole purpose is changing "ready to publish"
to "published" is not required when Git/GitHub already provides that publication
evidence. Create a post-push documentation correction only when the repository would
otherwise contain a materially misleading state.

Long gates and diagnostics should write complete output to `.log` files, with the
terminal showing only the exit code and a concise summary. Full diffs are not the
default inspection mechanism; prefer `--name-status`, `--stat`, `--numstat` and
`--check`, with focused excerpts only when needed.

## Default progress view for later sessions

Before PLAN-004 closes:

```text
PLAN-004
  [x] Subphase A — published / closed
  [x] Subphase B — published / closed
  [ ] Subphase C — TASK-P04-004..013
  [ ] Subphase D — TASK-P04-014..017
```

After PLAN-004 closes:

```text
Post-PLAN-004 roadmap
  [ ] Package 1 — Product execution acceptance
  [ ] Package 2 — Operator workflow acceptance
  [ ] Package 3 — PLAN-005 convergence and acceptance closure
  [ ] Package 4 — Deployment, persistence resilience and service operations
  [ ] Package 5 — Production readiness and roadmap closure
```

## Session-resume rule

A later session should begin by reading, in this order:

1. `specs/006-execution/README.md`;
2. `specs/006-execution/F4-WORKFLOW-DECOMPOSITION.md` while PLAN-004 is active;
3. this file;
4. the frozen task file for the currently active plan.

The assistant should report progress using the compact execution view above while
using frozen task IDs internally for dependencies, TDD ownership and evidence.


## Activation evidence

PLAN-004 closed at functional revision `095abd4` after `TASK-P04-017` passed the
Subphase D exit gate. The transition condition recorded at the top of this file is therefore
satisfied. Package 1 — **Product execution acceptance** — subsequently closed at functional revision `0f2e656`; Package 2 — **Operator workflow acceptance** — is the next default execution boundary. Frozen PLAN-005 tasks remain authoritative underneath the package view.

## Package 1 closure evidence

Status: **Verified / closed — Product execution acceptance**

Functional commit:

```text
0f2e656d9661e72c30cf75b7daecbadbfa4ee468
fix: complete PLAN-005 Package 1 acceptance
```

Package-level gate summary: `/home/christiano/Downloads/yt-transcriber-plan005-package1-gate-summary-v3.txt`.

The closure revision satisfies the Package 1 mapping to `TASK-P05-001..007`:

- bounded queue/media/summary/storage behavior remains characterized and yt-dlp metadata/
  subtitle-listing network waits now carry a finite socket timeout;
- privacy-aware audit/health/error behavior retains the shared sanitizer boundary;
- representative slow duration inspection is proven not to monopolize an independent
  Telegram event-loop tick;
- terminal history does not block fresh admission and explicit reprocessing remains a
  fresh-Job operation under the active/pending duplicate guard;
- subtitle/ASR/diarization duration/language/canonical paths retain their frozen behavior;
- failed non-primary history/summary/export/video sends are recorded as operational
  delivery errors without mutating an already-completed Job;
- pending Telegram cancellation retains cooperative state semantics and clears no-longer-
  needed private staging source references/files.

The real host/environment evidence intentionally owned by PLAN-006 remains outside this
Package 1 closure. Package 2 — **Operator workflow acceptance** — is next.

