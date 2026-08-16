# F4 — Application/Telegram workflow decomposition

Status: **Active — execution subphase A / TASK-P04-001 published and closed; subphase B next**
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
| B | `TASK-P04-002..003` | execution/queue/cancel/recovery plus completed-history workflow | **Active — P04-002 locally closed; P04-003 next** |
| C | `TASK-P04-004..013` | derived data, search, summary and operational decomposition | Pending |
| D | `TASK-P04-014..017` | thin-Telegram closure, reliability, convergence and PLAN-004 exit gate | Pending |

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

## TASK-P04-003 — Next

Proceed to `TASK-P04-003`: move completed-history ordering, operator scoping,
positional selection and canonical-Markdown retrieval decisions into an application
capability. Keep command parsing, titles/formatting/buttons and send mechanics in
Telegram, and keep textual search separate.
