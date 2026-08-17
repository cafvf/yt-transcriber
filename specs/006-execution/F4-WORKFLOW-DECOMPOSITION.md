# F4 — Application/Telegram workflow decomposition

Status: **Verified / closed — PLAN-004 completed at Subphase D functional revision `095abd4`**
Plan: `PLAN-004`
Base revision: `7c52c0d1d8682f4a1b59d8eeb57324171fa42fc7`
Started: 2026-08-16

This file is a non-normative execution record. Frozen requirement, plan and
task ownership remains defined by `003-atomic-requirements`, `004-planning`
and `005-tasks`.

## PLAN-004 execution subphases

For execution convenience, PLAN-004 is being worked in four review/push
boundaries without changing any frozen task dependency or PLAN exit gate:

| Execution subphase | Approved task range | Purpose | State |
|---|---|---|---|
| A | `TASK-P04-001` | establish application workflow/admission seam | **Published / closed** |
| B | `TASK-P04-002..003` | execution/queue/cancel/recovery plus completed-history workflow | **Published / closed** |
| C | `TASK-P04-004..013` | derived data, search, summary and operational decomposition | **Verified / closed at `0e2bb0a`** |
| D | `TASK-P04-014..017` | thin-Telegram closure, reliability, convergence and PLAN-004 exit gate | **Verified / closed at `095abd4`** |

The existing F4/F5 phase definitions remain authoritative as the execution
view inherited from frozen tasks. These subphases are only smaller review and
push boundaries inside PLAN-004.

## TASK-P04-001 — Establish application workflow boundary and extract submission/dedup/reprocess admission

Status: **Verified / closed**

Functional commit:

```text
a68ba1c0228d27b723f223d6b8b1c69a407155c0
refactor: extract application admission workflow
```

### Implemented boundary

P04-001 established `application.workflows.admission` as the first portable
application-workflow seam.

Application now owns:

- YouTube admission validation;
- duplicate admission decisions based on canonical video identity plus requested language;
- queue-capacity admission policy through a transport-neutral queue snapshot;
- explicit `/redo` semantics as creation of a fresh `Job`, not history reuse;
- private-media metadata admission rules;
- private-media two-phase prepare/commit admission;
- initial `Job` and request-context persistence collaboration.

Telegram remains responsible for:

- command and URL parsing;
- allowed-audience enforcement;
- user-facing rejection/presentation text;
- media download mechanism;
- queue enqueue mechanics;
- Telegram-specific progress/send behavior.

The application workflow consumes `QueueAdmissionState` and `QueuedSubmission`
rather than `SequentialJobQueue`, preserving TASK-P04-002 ownership of queue,
execution, cancellation and recovery.

`RequestContextSaver` is injected as a narrow callable when needed. This keeps
request-context persistence collaboration outside Telegram policy while
preserving brownfield duck-typed repository doubles during the reversible
migration.

### TDD / characterization evidence

Initial Red:

```text
application admission workflow absent
legacy Telegram-owned admission methods still present
```

The first Green extraction exposed four existing Telegram regression failures:

```text
test_redo_enqueues_fresh_processing
test_audio_voice_and_document_are_validated_then_enqueued[audio]
test_audio_voice_and_document_are_validated_then_enqueued[voice]
test_audio_voice_and_document_are_validated_then_enqueued[document]
```

Root cause was not product behavior: the first extraction called
`repository.save_request_context()` directly, while existing brownfield
Telegram doubles are deliberately duck-typed and do not all inherit the
`JobRepository` default method.

The fix introduced the narrow injectable `RequestContextSaver` collaboration
instead of weakening tests or forcing infrastructure-test doubles to inherit a
new concrete shape.

Focused verification after the repair:

```text
138 passed / 3 deselected
mypy: 113 source files / zero issues
legacy Telegram admission-method scan: empty
application -> Telegram import scan: empty
git diff --check: green
```

### Full local gate

The functional revision was verified before commit:

```text
Ruff auto-fix: green
Ruff format: 217 files unchanged
Ruff strict: green
format check: 217 files formatted
mypy: 113 source files / zero issues
security scanner: clean
Gitleaks: 50 commits / ~3.05 MB / no leaks

default gate:
  891 collected
  35 deselected
  856 passed

integration gate:
  891 collected
  856 deselected
  35 passed

compileall: green
pre-commit security hooks: green
final Ruff/format/mypy: green
git diff --check: green
```

### Conformance evidence

P04-001 added executable checks proving:

- the application admission workflow imports no infrastructure/Telegram code;
- the Telegram adapter no longer owns `_validate_incoming_media`;
- the Telegram adapter no longer owns `_is_already_queued`;
- the Telegram adapter no longer owns `_create_persisted_job`;
- Telegram delegates to `admit_youtube_submission`,
  `prepare_validated_media_submission` and `commit_media_submission`.

No product capability was added. No frozen normative requirement, plan or task
text was modified.

### Post-push regression repair

Remote review after the initial Subphase A publication found one
behavior-preservation regression in the YouTube admission presentation:
newline escapes had been double-escaped, producing a visible literal `\\n`
instead of line breaks.

The defect was routed back to its behavior owner, `TASK-P04-001`, and repaired
in functional commit:

```text
8beea3d
fix: preserve admission message newlines
```

Regression coverage now requires real line breaks in the `/redo` admission
message and rejects literal backslash-n output.

Verification recorded for the repair:

```text
focused /redo regression: 2 passed
P04-001 regression set: 96 passed
Ruff auto-fix / format / strict: green
mypy: 113 source files / zero issues
security scanner: clean
Gitleaks: 52 commits / ~3.08 MB / no leaks
default gate: 856 passed / 35 deselected
integration gate: 35 passed / 856 deselected
pre-commit security hooks: green
git diff --check: green
```

This repair did not change the P04-001 architectural boundary or any frozen
normative requirement.

## Next execution subphase

Proceed to **Subphase B — TASK-P04-002..003**:

1. `TASK-P04-002` — application-owned execution, queue, cancellation and recovery coordination;
2. `TASK-P04-003` — completed-history selection and retrieval workflow.

Subphase B must preserve the admission seam established by P04-001 and the
closed PLAN-003 architecture invariants.

## TASK-P04-002 — Application-owned execution, queue, cancellation and recovery coordination

Status: **Verified / locally closed — Subphase B not yet published**

Functional commit:

```text
d8055251f83f6fc400f6fe07b0f1e71425d9c289
refactor: move execution coordination to application
```

### Implemented boundary

P04-002 moved these portable responsibilities to Application:

- sequential queue implementation and queue state;
- creation and propagation of one cooperative cancellation token per queued item;
- Job lifecycle transitions for execution start, unexpected failure, pending cancellation and primary-delivery outcome;
- recoverable-pending startup result pairing `Job` with the validated `JobRequestContext`.

Telegram keeps queue/status rendering, progress-message editing, send/retry mechanics,
transport-facing recovery notifications and the current Telegram-specific execution payload.

`infrastructure.telegram.job_queue` remains temporarily as a compatibility re-export;
it no longer defines `SequentialJobQueue`. Final migration-scaffolding removal remains
owned by `TASK-P04-014`.

No checkpoint/resume behavior was introduced.

### Characterization and TDD evidence

Brownfield characterization showed that, before P04-002:

- `SequentialJobQueue` was implemented under `infrastructure.telegram`;
- `JobPayload` owned a `threading.Event` while the queue owned a separate cancellation event;
- the pipeline received cancellation from the Telegram payload;
- primary-delivery terminal lifecycle helpers were private methods on `TelegramBotAdapter`;
- recoverable startup results returned `Job` values without carrying the validated request context.

The first focused Green exposed one surviving brownfield test coupled to the old owner:

```text
1 failed / 122 passed / 3 deselected
test_terminal_persistence_failure_is_not_silently_suppressed
```

The production behavior was not restored to Telegram. The same invariant was moved to
`ExecutionLifecycleService`: a terminal persistence failure must propagate rather than
being silently suppressed.

After that ownership correction:

```text
focused tests: 123 passed / 3 deselected
Ruff: green
format: green
```

The focused support script then stopped because it invoked `uv run mypy` without a
target. This was a support-script defect, not a source failure. The repository command
was run explicitly:

```text
uv run mypy src
Success: no issues found in 115 source files
```

Ownership scans were verified:

```text
SequentialJobQueue definition under infrastructure.telegram: absent
cancel_event=payload.cancel_event in Telegram adapter: absent
cancel_event=item.cancel_event in Telegram adapter: present
ExecutionLifecycleService delegation in Telegram adapter: present
git diff --cached --check: green
```

### Full local gate

The final P04-002 worktree passed the standard PLAN-004 full gate:

```text
Ruff auto-fix / format / strict: green
format check: 221 files formatted
mypy: 115 source files / zero issues
security scanner: clean
Gitleaks: 54 commits / ~3.08 MB / no leaks

default gate:
  899 collected
  35 deselected
  864 passed

integration gate:
  899 collected
  864 deselected
  35 passed

pre-commit sensitive-file/token hooks: green
final Ruff/format/mypy: green
```

### REQ-ARC-003 acceptance evidence

- **AC-01:** queue behavior is exercised by Application tests without Telegram classes.
- **AC-02:** application lifecycle tests cover persisted start, cancellation, unexpected failure and primary-delivery terminal outcomes.
- **AC-03:** the queue-owned application cancellation token is the same token passed into the transcription use case.
- **AC-04:** startup recovery returns a recoverable `Job` together with its validated `JobRequestContext`, rather than requiring reconstruction from a Telegram payload.

No product capability was added and no frozen normative requirement, plan or task text
was modified.

## TASK-P04-003 — Application-owned completed-history workflow

Status: **Verified / published / closed**

Functional commit:

```text
bb7ccd9779cb7fffff731900f28719e29ae6115a
refactor: move completed history workflow to application
```

### Implemented boundary

P04-003 moved the portable completed-history policy to Application:

- completed-only filtering;
- per-user/operator scoping;
- newest-first ordering;
- one-based positional selection;
- canonical-Markdown retrieval state.

The Application workflow does not perform direct filesystem I/O. Markdown
availability is supplied through an injected probe; Telegram keeps the concrete
filesystem mechanism and maps application retrieval states to user-facing
messages.

Telegram retains:

- command parsing;
- title metadata lookup and prefetch;
- history-line formatting;
- user-facing error/help text;
- document-send mechanics;
- Telegram-specific presentation state.

Textual search remains separate and is not merged into the completed-history
workflow.

### Characterization and TDD evidence

The initial P04-003 characterization confirmed that completed-history filtering,
ordering and positional selection still lived under
`infrastructure.telegram.history`, and the adapter delegated those decisions to
the Telegram-owned collaboration object.

After the production boundary was moved, the first focused gate stopped during
test collection because a brownfield Telegram command test still imported the
removed `HistoryCollaboration` owner.

The correction did not restore the old production owner:

- the obsolete Telegram test that duplicated portable filtering/order/selection
  was removed;
- equivalent behavior remains covered in
  `tests/unit/application/workflows/test_history.py`;
- the Telegram presentation test was retargeted to `HistoryPresentation`.

Final focused gate:

```text
82 passed
mypy: 116 source files / zero issues
Ruff: green
ownership scans: green
git diff --check: green
```

### Full local gate

The final P04-003 worktree passed the explicit full repository gate:

```text
Ruff auto-fix / format / strict: green
format check: 224 files
mypy: 116 source files / zero issues
local security scanner: clean
Gitleaks: 56 commits / ~3.10 MB / no leaks

default gate:
  907 collected
  35 deselected
  872 passed

integration gate:
  907 collected
  872 deselected
  35 passed

compileall: green
pre-commit sensitive-file/token hooks: green
final Ruff/format/mypy: green
git diff --check: green
```

### REQ-ARC-002 acceptance contribution

P04-003 advances the portable-workflow requirement by making completed-history
selection/retrieval policy exerciseable without Telegram classes while leaving
Telegram responsible for protocol parsing and presentation.

No product capability was added. No frozen normative requirement, plan or task
text was modified.

## Subphase B — Local closure

Subphase B (`TASK-P04-002..003`) is now locally complete:

- `TASK-P04-002`: application-owned execution, queue, cancellation and recovery
  coordination — locally closed;
- `TASK-P04-003`: application-owned completed-history workflow — locally closed.

Subphase B passed its combined convergence gate and was published to
`origin/main` at `b9f2eba7e005af87ec7a97ffe6c0e830fdeedbdc`.

Execution is intentionally paused before Subphase C for review/discussion.


## Subphase C — closure evidence

Status: **Verified / closed**

Functional commit:

```text
0e2bb0ae4cb4131a99be7e661309bb5dba16a894
refactor: complete PLAN-004 Subphase C decomposition
```

Gate run recorded at: `20260816T230554Z`.

### Implemented boundary

Subphase C closes `TASK-P04-004..013` without changing frozen product scope.

The functional revision establishes:

- explicit derived-artifact association with `Job` and canonical transcript identity;
- explicit textual-search document lifecycle and canonical-source association;
- separation of Job lifecycle persistence from search indexing/query semantics;
- application-owned textual-search orchestration;
- application-owned transcript edit/export/video-derivative orchestration;
- application-owned summary selection, chunking/reduction, prompt/output and retry policy,
  with text-generation transport and concrete tokenizer integration remaining infrastructure;
- bounded private application/audit/operational-error logging;
- explicit reconstructible-cache ownership and safe cleanup;
- purpose-specific operational probes/stores/cleanup capabilities instead of direct
  external I/O in application policy;
- application-owned health, last-error, cache-clear and retention orchestration.

The runtime composition delegates these portable workflows through Application-owned
capabilities. Residual Telegram migration scaffolding is intentionally left for the
single thin-transport closure owner, `TASK-P04-014`, rather than being removed early.

No translation semantics, semantic search, checkpoint resume, multi-user behavior or
knowledge-system integration was introduced.

### TDD / characterization and gate evidence

The Subphase C gate runner executed the focused characterization/regression groups,
repository quality checks, security checks, default and integration pytest gates,
compileall, pre-commit coverage for tracked plus newly created files, and final
immutable Ruff/format/mypy/diff checks.

Recorded command outcomes:

- `focused_application` — exit `0`
- `focused_persistence_search` — exit `0`
- `focused_operational_storage` — exit `0`
- `focused_existing_regressions` — exit `0`
- `ruff_fix` — exit `0`
- `ruff_format` — exit `0`
- `ruff_strict` — exit `0`
- `format_check` — exit `0`
- `mypy` — exit `0`
- `secret_scan` — exit `0`
- `gitleaks` — exit `0`
- `pytest_default` — exit `0`
- `pytest_integration` — exit `0`
- `compileall` — exit `0`
- `benchmark_compile` — exit `0`
- `precommit` — exit `0`
- `final_ruff` — exit `0`
- `final_format` — exit `0`
- `final_mypy` — exit `0`
- `diff_check` — exit `0`

The complete command output was written to temporary local gate logs by the gate
runner. Long-lived execution evidence is this versioned closure record plus the Git
history; readiness evidence does not depend on indefinite runtime-log retention.

### Requirement/task closure map

- `TASK-P04-004` / `REQ-DATA-005`: derived artifact association and authority.
- `TASK-P04-005` / `REQ-DATA-011`: textual-search index data and lifecycle.
- `TASK-P04-006` / `REQ-ARC-007`: lifecycle persistence, indexing and search separation.
- `TASK-P04-007`: textual-search application workflow.
- `TASK-P04-008`: transcript edit/export/video-derivative orchestration.
- `TASK-P04-009` / `REQ-ARC-008`: application summary policy and infrastructure
  text-generation/tokenizer mechanisms.
- `TASK-P04-010` / `REQ-DATA-006`: bounded private operational logs.
- `TASK-P04-011` / `REQ-DATA-007`: reconstructible cache lifecycle.
- `TASK-P04-012` / `REQ-ARC-009`: operational policy separated from external I/O.
- `TASK-P04-013`: operational-command orchestration and retention invocation.

## Next execution subphase after C

Proceed to **Subphase D — `TASK-P04-014..017`** only after this documentation closure
has been committed and the Subphase C publication boundary has been pushed/verified.

Subphase D owns thin-Telegram closure, deterministic reliability/failure isolation,
final cohesive-refactor convergence and the PLAN-004 exit gate.


## Subphase D — PLAN-004 closure evidence

Status: **Verified / closed — PLAN-004 exit gate passed**

Functional commit:

```text
095abd46d73659e67b0d5cac4b4fe7f07fff43f7
refactor: complete PLAN-004 Subphase D convergence
```

Gate run recorded at: `20260817T001958Z`.

### Final convergence

Subphase D closes `TASK-P04-014..017` without adding product scope.

The functional revision:

- removes the active parallel concrete-service graph from `TelegramBotAdapter`;
- retains `HistoryPresentation` only as Telegram-side presentation/title formatting, while
  completed-history selection remains Application-owned;
- delegates search, rename, summary, exports/video derivatives and operational commands only
  through Application workflows/capabilities;
- moves private staged-source cleanup behind an Application service plus the existing
  purpose-specific owned-artifact cleanup port;
- injects completed-history, lifecycle and startup-recovery capabilities at composition;
- isolates best-effort derived completion observers from already-persisted canonical
  `COMPLETED` state while preserving propagation of canonical persistence failures;
- characterizes repeated startup reconciliation as idempotent once terminal state is reached;
- removes the obsolete history-search compatibility port/service and empty speculative
  `domain.events` / `domain.pipeline` package shells;
- removes persistence-shaped output-path parameters from the pure Application summary policy;
- keeps the concrete summarization compatibility façade passive and outside the production
  runtime graph because it remains useful for existing adapter-level compatibility tests and
  does not compete with the Application workflow owner.

No generic storage abstraction, translation behavior, checkpoint/resume semantics or new
architecture layer was introduced.

### PLAN-004 exit-gate evidence

- `thin_transport` — exit `0`
- `lifecycle_reliability` — exit `0`
- `portable_workflows` — exit `0`
- `persistence_search` — exit `0`
- `provider_and_summary_boundaries` — exit `0`
- `ruff_fix` — exit `0`
- `ruff_format` — exit `0`
- `ruff_strict` — exit `0`
- `format_check` — exit `0`
- `mypy` — exit `0`
- `secret_scan` — exit `0`
- `gitleaks` — exit `0`
- `pytest_default` — exit `0`
- `pytest_integration` — exit `0`
- `compileall` — exit `0`
- `benchmark_compile` — exit `0`
- `benchmark_smoke` — exit `0`
- `precommit` — exit `0`
- `final_ruff` — exit `0`
- `final_format` — exit `0`
- `final_mypy` — exit `0`
- `diff_check` — exit `0`

The gate covers thin-transport conformance, lifecycle failure isolation, startup recovery
idempotency, portable workflow tests, SQLite FTS/fallback behavior, provider/summary
boundaries, security scans, full default/integration pytest, compileall, pre-commit and
final immutable Ruff/format/mypy/diff checks.

### Requirement/task closure map

- `TASK-P04-014` / `REQ-ARC-002`: final thin-Telegram ownership closure.
- `TASK-P04-015` / `REQ-NFR-001`: deterministic lifecycle and failure isolation.
- `TASK-P04-016` / `REQ-NFR-005`: cohesive convergence and obsolete-surface cleanup.
- `TASK-P04-017`: PLAN-004 exit gate and closure evidence.

## PLAN-004 closed

All PLAN-004 execution subphases A–D are closed. The simplified post-PLAN-004 execution
view in `POST-PLAN-004-EXECUTION-ROADMAP.md` is now active. The next management boundary is
**Package 1 — Product execution acceptance**, backed by the still-authoritative frozen
PLAN-005 task graph.
