# PLAN-005 Tasks — Functional and non-functional reconnection

Version: **1.0.0**
Status: **Approved / Frozen**
Derived from: **004-planning v1.0.0 (Approved / Frozen)**

## Execution rule

These tasks reconnect and accept frozen operator behavior over the repaired architecture. They may make the smallest missing application/product change needed for their REQ, but they must not recreate lower-layer domain/data/port policy already owned by PLAN-001..004. A failure in an upstream contract is routed back to its owner.

## TASK-P05-001 — Bounded resource consumption and external waits

**Primary REQ:** `REQ-NFR-002`
**Task role:** **change / acceptance owner**
**Dependencies:** `TASK-P04-017`

### Implementation intent

The baseline SHALL bound queue occupancy, media/duration/artifact/log/cache/token operations and external waits so an approved request cannot consume unbounded application resources.

**Current brownfield focus:** No specific brownfield defect is singled out; preserve approved behavior while establishing the required contract.

**Likely touchpoints:** Queue/media/duration/token/log/cache/artifact limits, timeouts and bounded external waits.

### Red

Create or strengthen the lowest useful tests that express the frozen acceptance boundary:

- AC-01: Queue capacity is configured and enforced before acceptance.
- AC-02: Unknown duration cannot bypass the configured maximum-duration protection.
- AC-03: Subprocess/network/provider waits use finite timeout and/or cooperative cancellation semantics where the underlying operation permits.
- AC-04: Summary input/output/token/chunk budgets are configured and bounded.
- AC-05: Operational logs, cache and retention-managed storage have explicit bounded lifecycle policies.

If all acceptance criteria are already satisfied, record characterization evidence instead of manufacturing an artificial failing test. For host-only or environment-only criteria, a failing preflight/rehearsal criterion is valid Red evidence; do not fabricate a unit-test substitute.

### Green

Implement the minimum coherent change required to satisfy the failing acceptance evidence while preserving all upstream frozen behavior and the current plan ownership boundary.

### Refactor / convergence

Remove temporary duplication introduced by the migration, keep one owner for the policy/capability, and run relevant architecture/contract/conformance checks before considering the task complete.

### Completion evidence

- resource-limit tests
- timeout/cancellation tests
- summary budget tests
- retention/cache/log lifecycle tests

Also record the quality gates actually run and any environment-gated evidence deferred to PLAN-006.

## TASK-P05-002 — Actionable privacy-aware observability

**Primary REQ:** `REQ-NFR-003`
**Task role:** **change / acceptance owner**
**Dependencies:** `TASK-P04-017`

### Implementation intent

Operational observability SHALL make lifecycle, health, failure and rehearsal decisions diagnosable with minimal private content and stable event/status semantics.

**Current brownfield focus:** No specific brownfield defect is singled out; preserve approved behavior while establishing the required contract.

**Likely touchpoints:** Audit/health/error/progress/status semantics and privacy-aware observability.

**Integration note:** Consume the shared sanitizer/private-log semantics from PLAN-001/004; do not create a parallel logging or redaction subsystem.

### Red

Create or strengthen the lowest useful tests that express the frozen acceptance boundary:

- AC-01: Audit events identify operation, Job/opaque correlation, stage and outcome without transcript bodies.
- AC-02: Health/error reports distinguish blockers, warnings and recoverable artifact availability.
- AC-03: Logs provide enough sanitized context for the operator to choose a documented next action.
- AC-04: Evidence records identify revision/environment/result without credentials or private transcript payloads.

If all acceptance criteria are already satisfied, record characterization evidence instead of manufacturing an artificial failing test. For host-only or environment-only criteria, a failing preflight/rehearsal criterion is valid Red evidence; do not fabricate a unit-test substitute.

### Green

Implement the minimum coherent change required to satisfy the failing acceptance evidence while preserving all upstream frozen behavior and the current plan ownership boundary.

### Refactor / convergence

Remove temporary duplication introduced by the migration, keep one owner for the policy/capability, and run relevant architecture/contract/conformance checks before considering the task complete.

### Completion evidence

- observability contract tests
- health/lasterror tests
- evidence-review checklist

Also record the quality gates actually run and any environment-gated evidence deferred to PLAN-006.

## TASK-P05-003 — Non-blocking Telegram transport responsiveness

**Primary REQ:** `REQ-NFR-007`
**Task role:** **change / acceptance owner**
**Dependencies:** `TASK-P04-017`, `TASK-P05-001`

### Implementation intent

Long synchronous CPU, filesystem, subprocess or provider work initiated by Telegram handlers SHALL not monopolize the Telegram async event loop; the transport SHALL remain responsive to independent lightweight control/interaction work within the limits of the sequential processing model.

**Current brownfield focus:** No specific brownfield defect is singled out; preserve approved behavior while establishing the required contract.

**Likely touchpoints:** Telegram asyncio handlers, thread/off-loop execution of synchronous work and responsiveness tests.

### Red

Create or strengthen the lowest useful tests that express the frozen acceptance boundary:

- AC-01: Known long synchronous processing is executed outside the Telegram event-loop thread or exposed through an asynchronous capability.
- AC-02: Finite subprocess/provider waits do not block unrelated async callbacks solely because a synchronous function was called directly from a handler.
- AC-03: Progress/control callbacks can continue to be serviced according to the frozen sequential-processing contract while expensive work runs.
- AC-04: Tests demonstrate that representative slow duration/subprocess or application work does not block an independent event-loop tick.

If all acceptance criteria are already satisfied, record characterization evidence instead of manufacturing an artificial failing test. For host-only or environment-only criteria, a failing preflight/rehearsal criterion is valid Red evidence; do not fabricate a unit-test substitute.

### Green

Implement the minimum coherent change required to satisfy the failing acceptance evidence while preserving all upstream frozen behavior and the current plan ownership boundary.

### Refactor / convergence

Remove temporary duplication introduced by the migration, keep one owner for the policy/capability, and run relevant architecture/contract/conformance checks before considering the task complete.

### Completion evidence

- async responsiveness tests
- regression test analogous to ffprobe non-blocking coverage

Also record the quality gates actually run and any environment-gated evidence deferred to PLAN-006.

## TASK-P05-004 — Submit supported media and explicitly reprocess as a new Job

**Primary REQ:** `REQ-FUNC-001`
**Task role:** **change / acceptance owner**
**Dependencies:** `TASK-P04-017`, `TASK-P05-001`

### Implementation intent

The authorized operator SHALL be able to submit supported YouTube references and Telegram audio/voice/audio-document media and SHALL be able to explicitly reprocess a YouTube source as a distinct new Job, subject to source validation, queue capacity and the frozen active/pending deduplication policy.

**Current brownfield focus:** Current deduplication exists inside the Telegram adapter and compares only active/pending `video_id + requested_language`; the application layer must preserve that frozen behavior while taking ownership of the policy.

**Likely touchpoints:** Submission/reprocess application flows plus Telegram URL/audio entry acceptance.

### Red

Create or strengthen the lowest useful tests that express the frozen acceptance boundary:

- AC-01: Supported Telegram audio, voice, audio-document and YouTube URL paths are accepted when source-specific constraints are satisfied.
- AC-02: Unsupported source/media type, explicit unsupported language request, source-specific size violation or full queue is rejected explicitly.
- AC-03: A YouTube submission is an active duplicate only when the current/pending queue already contains the same canonical video identity with the same requested-language value; terminal historical Jobs do not themselves block a new submission.
- AC-04: Explicit `/redo` creates a distinct new Job when accepted and never reopens or mutates a terminal historical Job; it remains subject to the same active/pending duplicate guard.

If all acceptance criteria are already satisfied, record characterization evidence instead of manufacturing an artificial failing test. For host-only or environment-only criteria, a failing preflight/rehearsal criterion is valid Red evidence; do not fabricate a unit-test substitute.

### Green

Implement the minimum coherent change required to satisfy the failing acceptance evidence while preserving all upstream frozen behavior and the current plan ownership boundary.

### Refactor / convergence

Remove temporary duplication introduced by the migration, keep one owner for the policy/capability, and run relevant architecture/contract/conformance checks before considering the task complete.

### Completion evidence

- submission/dedup/reprocess application tests
- Telegram adapter conformance tests

Also record the quality gates actually run and any environment-gated evidence deferred to PLAN-006.

## TASK-P05-005 — Process media through truthful subtitle, ASR and diarization paths

**Primary REQ:** `REQ-FUNC-002`
**Task role:** **change / acceptance owner**
**Dependencies:** `TASK-P04-017`, `TASK-P05-004`

### Implementation intent

Accepted media SHALL follow the approved source-specific shortcut/common-processing path and produce truthful canonical transcript evidence, falling back from unsuitable YouTube subtitles to audio/ASR and never bypassing language or duration constraints through fabricated metadata.

**Current brownfield focus:** No specific brownfield defect is singled out; preserve approved behavior while establishing the required contract.

**Likely touchpoints:** Source acquisition, subtitle quality/fallback, conversion, ASR, diarization and canonical render acceptance.

### Red

Create or strengthen the lowest useful tests that express the frozen acceptance boundary:

- AC-01: An eligible manual or accepted automatic non-translated subtitle may skip ASR after integrity/quality checks.
- AC-02: Missing, unsuitable or corrupt subtitle falls back to the approved audio/ASR path.
- AC-03: Unknown source language stays unknown until an operator constraint or truthful source/ASR observation exists.
- AC-04: Without an explicit operator language constraint, an independently observed ASR language outside the allowlist is rejected rather than relabeled.
- AC-05: With an explicit operator language constraint, the constraint may drive forced decoding but any independent observed language/confidence remains separately attributable and is not rewritten.
- AC-06: Unknown duration is established as within limit before expensive ASR/diarization or the request is rejected.
- AC-07: The audio path converts, selects runtime policy, transcribes, diarizes and persists the required canonical structured/Markdown evidence.

If all acceptance criteria are already satisfied, record characterization evidence instead of manufacturing an artificial failing test. For host-only or environment-only criteria, a failing preflight/rehearsal criterion is valid Red evidence; do not fabricate a unit-test substitute.

### Green

Implement the minimum coherent change required to satisfy the failing acceptance evidence while preserving all upstream frozen behavior and the current plan ownership boundary.

### Refactor / convergence

Remove temporary duplication introduced by the migration, keep one owner for the policy/capability, and run relevant architecture/contract/conformance checks before considering the task complete.

### Completion evidence

- pipeline behavior tests
- subtitle fallback/integrity tests
- language/duration regression tests
- canonical-persistence failure tests

Also record the quality gates actually run and any environment-gated evidence deferred to PLAN-006.

## TASK-P05-006 — Primary and derivative delivery outcomes

**Primary REQ:** `REQ-FUNC-003`
**Task role:** **change / acceptance owner**
**Dependencies:** `TASK-P04-017`

### Implementation intent

Delivery SHALL distinguish primary-transcription completion from retrieval/derived-artifact sends: only primary transcript delivery controls the original Job `delivering→completed|delivery_failed` terminal outcome.

**Current brownfield focus:** No specific brownfield defect is singled out; preserve approved behavior while establishing the required contract.

**Likely touchpoints:** Primary transcript delivery versus history/derived sends and Job terminal outcomes.

### Red

Create or strengthen the lowest useful tests that express the frozen acceptance boundary:

- AC-01: Required primary artifacts remain locally recoverable when primary delivery retries exhaust, subject to retention policy.
- AC-02: Successful primary delivery marks the Job `completed`.
- AC-03: Failure to send history, summary, export or video for an already completed Job does not retroactively change that completed lifecycle.
- AC-04: Delivery errors are sanitized and recorded as operational errors where appropriate.

If all acceptance criteria are already satisfied, record characterization evidence instead of manufacturing an artificial failing test. For host-only or environment-only criteria, a failing preflight/rehearsal criterion is valid Red evidence; do not fabricate a unit-test substitute.

### Green

Implement the minimum coherent change required to satisfy the failing acceptance evidence while preserving all upstream frozen behavior and the current plan ownership boundary.

### Refactor / convergence

Remove temporary duplication introduced by the migration, keep one owner for the policy/capability, and run relevant architecture/contract/conformance checks before considering the task complete.

### Completion evidence

- delivery/retry tests
- derived-delivery failure isolation tests
- manual-recovery evidence

Also record the quality gates actually run and any environment-gated evidence deferred to PLAN-006.

## TASK-P05-007 — Observe queue/status and cancel scoped work

**Primary REQ:** `REQ-FUNC-004`
**Task role:** **change / acceptance owner**
**Dependencies:** `TASK-P04-017`

### Implementation intent

The operator SHALL receive a consistent read-only view of active/pending work and SHALL be able to cooperatively cancel the active Job, pending Jobs, or both without changing unrelated work.

**Current brownfield focus:** No specific brownfield defect is singled out; preserve approved behavior while establishing the required contract.

**Likely touchpoints:** `/status`, queue aliases, cancel/clearqueue/cancelall and scoped cancellation behavior.

### Red

Create or strengthen the lowest useful tests that express the frozen acceptance boundary:

- AC-01: Status/queue inspection does not reorder or mutate work.
- AC-02: Pending cancellation removes the targeted queue entry and persists the approved cancelled outcome.
- AC-03: Active cancellation propagates a cooperative signal and need not interrupt an already-running external operation instantaneously.
- AC-04: Cancelled pending Telegram staging is cleaned when no approved recovery path still requires it.
- AC-05: Empty/no-match outcomes are truthful.

If all acceptance criteria are already satisfied, record characterization evidence instead of manufacturing an artificial failing test. For host-only or environment-only criteria, a failing preflight/rehearsal criterion is valid Red evidence; do not fabricate a unit-test substitute.

### Green

Implement the minimum coherent change required to satisfy the failing acceptance evidence while preserving all upstream frozen behavior and the current plan ownership boundary.

### Refactor / convergence

Remove temporary duplication introduced by the migration, keep one owner for the policy/capability, and run relevant architecture/contract/conformance checks before considering the task complete.

### Completion evidence

- queue/status tests
- pending/active cancellation tests
- staging cleanup tests

Also record the quality gates actually run and any environment-gated evidence deferred to PLAN-006.

## TASK-P05-008 — Browse and retrieve completed history

**Primary REQ:** `REQ-FUNC-005`
**Task role:** **change / acceptance owner**
**Dependencies:** `TASK-P04-017`

### Implementation intent

The operator SHALL be able to browse completed history and retrieve saved canonical Markdown using deterministic current positional ordering without treating those positions as durable identifiers or silently reprocessing missing evidence.

**Current brownfield focus:** No specific brownfield defect is singled out; preserve approved behavior while establishing the required contract.

**Likely touchpoints:** `/list`/`/last`, positional history selection and canonical Markdown availability.

**Integration note:** History browsing and textual search remain separate capabilities even if they share completed-Job data.

### Red

Create or strengthen the lowest useful tests that express the frozen acceptance boundary:

- AC-01: Displayed numeric indexes are positions over the current completed ordering and may change when that ordering changes.
- AC-02: History is scoped to the authorized operator and completed in-scope Jobs.
- AC-03: `/last` or indexed retrieval returns the saved Markdown associated with the selected completed Job.
- AC-04: Missing/unreadable required canonical history evidence is reported explicitly and does not trigger reprocessing.

If all acceptance criteria are already satisfied, record characterization evidence instead of manufacturing an artificial failing test. For host-only or environment-only criteria, a failing preflight/rehearsal criterion is valid Red evidence; do not fabricate a unit-test substitute.

### Green

Implement the minimum coherent change required to satisfy the failing acceptance evidence while preserving all upstream frozen behavior and the current plan ownership boundary.

### Refactor / convergence

Remove temporary duplication introduced by the migration, keep one owner for the policy/capability, and run relevant architecture/contract/conformance checks before considering the task complete.

### Completion evidence

- history ordering/selection tests
- missing-artifact tests
- privacy scoping tests

Also record the quality gates actually run and any environment-gated evidence deferred to PLAN-006.

## TASK-P05-009 — Text-search completed history

**Primary REQ:** `REQ-FUNC-013`
**Task role:** **change / acceptance owner**
**Dependencies:** `TASK-P04-017`

### Implementation intent

The operator SHALL be able to perform operator-scoped textual search over approved completed-history fields using SQLite FTS5 when available or the approved deterministic bounded textual fallback when FTS5 is unavailable.

**Current brownfield focus:** No specific brownfield defect is singled out; preserve approved behavior while establishing the required contract.

**Likely touchpoints:** `/search`, FTS5/fallback semantics, operator scope and deterministic bounded result behavior.

**Integration note:** History browsing and textual search remain separate capabilities even if they share completed-Job data.

### Red

Create or strengthen the lowest useful tests that express the frozen acceptance boundary:

- AC-01: Search is limited to completed Jobs belonging to the authorized operator scope.
- AC-02: FTS5 absence activates the approved bounded textual fallback without changing to semantic/vector search.
- AC-03: Search documents reflect approved transcript metadata/text, aliases and summary text according to the textual-index contract.
- AC-04: Returned snippets are compact, sanitized and do not expose private staging paths.

If all acceptance criteria are already satisfied, record characterization evidence instead of manufacturing an artificial failing test. For host-only or environment-only criteria, a failing preflight/rehearsal criterion is valid Red evidence; do not fabricate a unit-test substitute.

### Green

Implement the minimum coherent change required to satisfy the failing acceptance evidence while preserving all upstream frozen behavior and the current plan ownership boundary.

### Refactor / convergence

Remove temporary duplication introduced by the migration, keep one owner for the policy/capability, and run relevant architecture/contract/conformance checks before considering the task complete.

### Completion evidence

- SQLite FTS integration tests
- fallback tests
- search privacy/sanitization tests

Also record the quality gates actually run and any environment-gated evidence deferred to PLAN-006.

## TASK-P05-010 — Rename and merge speakers from canonical evidence

**Primary REQ:** `REQ-FUNC-006`
**Task role:** **change / acceptance owner**
**Dependencies:** `TASK-P04-017`

### Implementation intent

The operator SHALL be able to persist valid speaker aliases/merges and re-render Markdown and affected textual-search state from canonical structured transcript evidence without rerunning ASR/diarization or mutating canonical segment identity.

**Current brownfield focus:** No specific brownfield defect is singled out; preserve approved behavior while establishing the required contract.

**Likely touchpoints:** `/rename`, alias persistence, canonical re-render and search-index refresh.

### Red

Create or strengthen the lowest useful tests that express the frozen acceptance boundary:

- AC-01: Only existing speaker labels and non-empty alias values are accepted.
- AC-02: Assigning the same alias to multiple labels may represent an intentional merge.
- AC-03: Alias state persists durably with the Job/application record.
- AC-04: Missing canonical structured evidence fails explicitly; Markdown is not parsed as a substitute.
- AC-05: Affected textual-search state is explicitly refreshed.

If all acceptance criteria are already satisfied, record characterization evidence instead of manufacturing an artificial failing test. For host-only or environment-only criteria, a failing preflight/rehearsal criterion is valid Red evidence; do not fabricate a unit-test substitute.

### Green

Implement the minimum coherent change required to satisfy the failing acceptance evidence while preserving all upstream frozen behavior and the current plan ownership boundary.

### Refactor / convergence

Remove temporary duplication introduced by the migration, keep one owner for the policy/capability, and run relevant architecture/contract/conformance checks before considering the task complete.

### Completion evidence

- rename domain/application tests
- rerender tests
- search refresh tests

Also record the quality gates actually run and any environment-gated evidence deferred to PLAN-006.

## TASK-P05-011 — Generate a derived summary from canonical evidence

**Primary REQ:** `REQ-FUNC-007`
**Task role:** **change / acceptance owner**
**Dependencies:** `TASK-P04-017`, `TASK-P05-001`

### Implementation intent

The operator SHALL be able to generate a derived Markdown summary from canonical transcript evidence using the configured summary policy/backend without mutating canonical transcript state.

**Current brownfield focus:** No specific brownfield defect is singled out; preserve approved behavior while establishing the required contract.

**Likely touchpoints:** `/summary`, canonical input, application summary policy, derived association and search-index refresh.

### Red

Create or strengthen the lowest useful tests that express the frozen acceptance boundary:

- AC-01: A disabled/unavailable configured summary capability reports an explicit unavailable outcome.
- AC-02: Chunking, input/output token budgets and application-level adaptive subdivision remain bounded and configurable.
- AC-03: Successful summary records available model, chunk/tokenizer and generation provenance appropriate to the current implementation.
- AC-04: Disclosure to a non-local text-generation endpoint follows the approved explicit external-service configuration/security boundary.
- AC-05: A successful summary becomes part of the current textual-search document where summary text is an approved indexed field.
- AC-06: Provider errors are sanitized.

If all acceptance criteria are already satisfied, record characterization evidence instead of manufacturing an artificial failing test. For host-only or environment-only criteria, a failing preflight/rehearsal criterion is valid Red evidence; do not fabricate a unit-test substitute.

### Green

Implement the minimum coherent change required to satisfy the failing acceptance evidence while preserving all upstream frozen behavior and the current plan ownership boundary.

### Refactor / convergence

Remove temporary duplication introduced by the migration, keep one owner for the policy/capability, and run relevant architecture/contract/conformance checks before considering the task complete.

### Completion evidence

- summary application tests
- text-generation/tokenizer contract tests
- summary-search refresh tests
- security error tests

Also record the quality gates actually run and any environment-gated evidence deferred to PLAN-006.

## TASK-P05-012 — Generate transcript exports from canonical evidence

**Primary REQ:** `REQ-FUNC-008`
**Task role:** **change / acceptance owner**
**Dependencies:** `TASK-P04-017`

### Implementation intent

The operator SHALL be able to generate supported transcript export formats from canonical structured evidence and current speaker aliases without changing canonical transcript state.

**Current brownfield focus:** No specific brownfield defect is singled out; preserve approved behavior while establishing the required contract.

**Likely touchpoints:** TXT/JSON/SRT/VTT generation from canonical structured evidence and aliases.

**Integration note:** Transcript export and YouTube video derivative remain separate failure models/capabilities.

### Red

Create or strengthen the lowest useful tests that express the frozen acceptance boundary:

- AC-01: TXT, JSON, SRT and VTT outputs are generated from structured canonical evidence rather than by parsing Markdown.
- AC-02: Current persisted speaker aliases are reflected where the export format contains speaker text/labels.
- AC-03: Unsupported format or history position is reported explicitly.
- AC-04: Missing structured evidence is reported explicitly and is not reconstructed from Markdown or media.

If all acceptance criteria are already satisfied, record characterization evidence instead of manufacturing an artificial failing test. For host-only or environment-only criteria, a failing preflight/rehearsal criterion is valid Red evidence; do not fabricate a unit-test substitute.

### Green

Implement the minimum coherent change required to satisfy the failing acceptance evidence while preserving all upstream frozen behavior and the current plan ownership boundary.

### Refactor / convergence

Remove temporary duplication introduced by the migration, keep one owner for the policy/capability, and run relevant architecture/contract/conformance checks before considering the task complete.

### Completion evidence

- export-format tests
- speaker-alias export tests
- missing-evidence tests

Also record the quality gates actually run and any environment-gated evidence deferred to PLAN-006.

## TASK-P05-013 — Generate YouTube MP4 with selectable subtitles

**Primary REQ:** `REQ-FUNC-014`
**Task role:** **change / acceptance owner**
**Dependencies:** `TASK-P04-017`, `TASK-P05-001`

### Implementation intent

For an eligible completed YouTube Job, the operator SHALL be able to generate an MP4 derivative containing selectable subtitles from canonical transcript evidence without changing canonical transcript state.

**Current brownfield focus:** No specific brownfield defect is singled out; preserve approved behavior while establishing the required contract.

**Likely touchpoints:** YouTube video reacquisition, subtitle derivative generation, ffmpeg mux and send limits.

**Integration note:** Transcript export and YouTube video derivative remain separate failure models/capabilities.

### Red

Create or strengthen the lowest useful tests that express the frozen acceptance boundary:

- AC-01: Non-YouTube Jobs are rejected for this derivative.
- AC-02: Subtitles are generated from canonical structured evidence and current aliases.
- AC-03: Source video is reacquired from canonical YouTube identity through the YouTube adapter; authentication cookies remain boundary-confined.
- AC-04: Configured duration and output/download size limits are enforced.
- AC-05: Missing structured evidence or unavailable source produces an explicit derivative failure without mutating the completed Job.

If all acceptance criteria are already satisfied, record characterization evidence instead of manufacturing an artificial failing test. For host-only or environment-only criteria, a failing preflight/rehearsal criterion is valid Red evidence; do not fabricate a unit-test substitute.

### Green

Implement the minimum coherent change required to satisfy the failing acceptance evidence while preserving all upstream frozen behavior and the current plan ownership boundary.

### Refactor / convergence

Remove temporary duplication introduced by the migration, keep one owner for the policy/capability, and run relevant architecture/contract/conformance checks before considering the task complete.

### Completion evidence

- video-derivative tests
- ffmpeg command/integration tests
- source/security boundary tests

Also record the quality gates actually run and any environment-gated evidence deferred to PLAN-006.

## TASK-P05-014 — Inspect runtime health safely

**Primary REQ:** `REQ-FUNC-009`
**Task role:** **change / acceptance owner**
**Dependencies:** `TASK-P04-017`, `TASK-P05-002`, `TASK-P05-003`

### Implementation intent

The authorized operator SHALL be able to run a bounded, side-effect-minimized health assessment that classifies blocking/advisory conditions and returns sanitized actionable diagnostics without revealing secrets.

**Current brownfield focus:** No specific brownfield defect is singled out; preserve approved behavior while establishing the required contract.

**Likely touchpoints:** `/healthcheck` application probes, bounded execution and sanitized rendering.

### Red

Create or strengthen the lowest useful tests that express the frozen acceptance boundary:

- AC-01: Checks cover the current required runtime, configuration, dependency, storage and summary dimensions through approved probes.
- AC-02: Optional capability absence may be classified as warning rather than blocker when the baseline can otherwise operate.
- AC-03: Probe failure becomes a sanitized finding rather than a raw exception.
- AC-04: Healthcheck is not required to discover the systemd secret-file path or permissions; host preflight owns that evidence.

If all acceptance criteria are already satisfied, record characterization evidence instead of manufacturing an artificial failing test. For host-only or environment-only criteria, a failing preflight/rehearsal criterion is valid Red evidence; do not fabricate a unit-test substitute.

### Green

Implement the minimum coherent change required to satisfy the failing acceptance evidence while preserving all upstream frozen behavior and the current plan ownership boundary.

### Refactor / convergence

Remove temporary duplication introduced by the migration, keep one owner for the policy/capability, and run relevant architecture/contract/conformance checks before considering the task complete.

### Completion evidence

- healthcheck application tests with fake probes
- sanitization tests
- async responsiveness test

Also record the quality gates actually run and any environment-gated evidence deferred to PLAN-006.

## TASK-P05-015 — Inspect the latest relevant operational error

**Primary REQ:** `REQ-FUNC-010`
**Task role:** **change / acceptance owner**
**Dependencies:** `TASK-P04-017`, `TASK-P05-002`, `TASK-P05-003`

### Implementation intent

The operator SHALL be able to inspect the latest relevant failed/delivery-failed Job or operational error with truthful local-artifact availability and no implicit resend or terminal-state mutation.

**Current brownfield focus:** No specific brownfield defect is singled out; preserve approved behavior while establishing the required contract.

**Likely touchpoints:** `/lasterror` job/operational-error selection and truthful artifact availability.

### Red

Create or strengthen the lowest useful tests that express the frozen acceptance boundary:

- AC-01: No-error outcome is explicit.
- AC-02: Selection compares the most recent failed/delivery-failed Job timestamp with the most recent operator-scoped operational-error timestamp and returns the newer record; ties preserve the current operational-error precedence.
- AC-03: `delivery_failed` recovery information reports only artifacts that actually exist and remain available.
- AC-04: Raw prompts, provider bodies and secrets are not disclosed.
- AC-05: Inspection does not mutate terminal Job state.

If all acceptance criteria are already satisfied, record characterization evidence instead of manufacturing an artificial failing test. For host-only or environment-only criteria, a failing preflight/rehearsal criterion is valid Red evidence; do not fabricate a unit-test substitute.

### Green

Implement the minimum coherent change required to satisfy the failing acceptance evidence while preserving all upstream frozen behavior and the current plan ownership boundary.

### Refactor / convergence

Remove temporary duplication introduced by the migration, keep one owner for the policy/capability, and run relevant architecture/contract/conformance checks before considering the task complete.

### Completion evidence

- last-error precedence tests
- artifact-existence tests
- sanitization tests
- async responsiveness test

Also record the quality gates actually run and any environment-gated evidence deferred to PLAN-006.

## TASK-P05-016 — Safely clear reconstructible cache

**Primary REQ:** `REQ-FUNC-011`
**Task role:** **change / acceptance owner**
**Dependencies:** `TASK-P04-017`, `TASK-P05-003`

### Implementation intent

The operator SHALL be able to delete only the approved reconstructible model/tokenizer cache scope, with path containment and truthful feedback, without touching canonical/history data.

**Current brownfield focus:** No specific brownfield defect is singled out; preserve approved behavior while establishing the required contract.

**Likely touchpoints:** `/clearcache` owned reconstructible scope and safe feedback.

### Red

Create or strengthen the lowest useful tests that express the frozen acceptance boundary:

- AC-01: Unsafe, ambiguous or out-of-scope cache root is refused.
- AC-02: Missing cache is a benign empty/no-op result.
- AC-03: Partial deletion failures are sanitized and recorded.
- AC-04: Canonical Job/transcript/summary/history data remains intact.

If all acceptance criteria are already satisfied, record characterization evidence instead of manufacturing an artificial failing test. For host-only or environment-only criteria, a failing preflight/rehearsal criterion is valid Red evidence; do not fabricate a unit-test substitute.

### Green

Implement the minimum coherent change required to satisfy the failing acceptance evidence while preserving all upstream frozen behavior and the current plan ownership boundary.

### Refactor / convergence

Remove temporary duplication introduced by the migration, keep one owner for the policy/capability, and run relevant architecture/contract/conformance checks before considering the task complete.

### Completion evidence

- cache command tests
- path/symlink containment tests
- async responsiveness test

Also record the quality gates actually run and any environment-gated evidence deferred to PLAN-006.

## TASK-P05-017 — PLAN-005 exit-gate verification

**Primary REQ:** none; plan gate
**Task role:** **plan gate**
**Dependencies:** `TASK-P05-001`, `TASK-P05-002`, `TASK-P05-003`, `TASK-P05-004`, `TASK-P05-005`, `TASK-P05-006`, `TASK-P05-007`, `TASK-P05-008`, `TASK-P05-009`, `TASK-P05-010`, `TASK-P05-011`, `TASK-P05-012`, `TASK-P05-013`, `TASK-P05-014`, `TASK-P05-015`, `TASK-P05-016`

### Scope

Verify that every primary owner, support/foundation task and assurance task in PLAN-005 satisfies the frozen plan exit gate before work in the next plan is treated as implementation-ready. This task does not add product behavior or reimplement a failed criterion.

### Gate evidence

- All 12 frozen operator UCs have executable acceptance evidence.
- Application-level `SS-001`/`SS-002` behavior is covered; host evidence remains explicitly deferred to PLAN-006.
- All current command behaviors/aliases remain compatible except approved private-chat hardening.
- Resource-limit and event-loop responsiveness tests pass.
- Primary versus derived delivery lifecycle tests pass.
- Current environment-gated integration contracts retain or receive explicit equivalent evidence and are classified for PLAN-006 execution.

### Completion rule

Record commands/evidence, unresolved environment limitations and any failed criterion. A failed criterion MUST be routed to the task that owns the missing behavior or evidence; the gate itself does not patch around the failure. Shared operational evidence may be referenced rather than rerun when it was captured on the same closure revision and remains valid.
