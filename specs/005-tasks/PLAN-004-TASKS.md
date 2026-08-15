# PLAN-004 Tasks — Application ownership and persistence/search/operations decomposition

Version: **1.0.0**
Status: **Approved / Frozen**
Derived from: **004-planning v1.0.0 (Approved / Frozen)**

## Execution rule

PLAN-004 is deliberately decomposed **one portable workflow at a time**, as required by the frozen plan. Support/extraction tasks contribute to `REQ-ARC-002` without becoming parallel requirement owners; `TASK-P04-014` is the single closure owner for the thin-Telegram invariant. Cross-cutting NFR tasks are assurance owners: a failed criterion is routed back to the behavior-owning task rather than repaired twice.

## TASK-P04-001 — Establish application workflow boundary and extract submission/dedup/reprocess admission

**Primary REQ:** none; supports frozen requirements without closing them
**Supports:** `REQ-ARC-002`
**Task role:** **support / foundation**
**Dependencies:** `TASK-P03-014`

### Scope

Establish the practical application-workflow seam required by `REQ-ARC-002` and move submission/admission, deduplication and explicit reprocess-as-new-Job decisions out of Telegram infrastructure while keeping Telegram parsing/presentation and audience enforcement at the transport boundary. This is the first reversible workflow extraction; it does not close the whole thin-transport requirement.

**Integration note:** This foundation provides the application-workflow ownership seam consumed by TASK-P04-002 and later workflow extractions.

### Red / characterization

Characterize current direct URL/command/media admission, queue-full/dedup and `/redo` behavior without importing Telegram classes into the new application tests.

### Green

Introduce the minimum application use case/service boundary for admission/dedup/reprocess and delegate to it from Telegram. Preserve current commands, aliases and transport presentation.

### Refactor / convergence

Do not create a second source of policy truth. Remove temporary migration scaffolding when the owning closure task has replacement evidence.

### Completion evidence

- application admission/dedup/reprocess tests without Telegram classes;
- adapter delegation tests;
- no product behavior expansion.

## TASK-P04-002 — Application-owned execution, queue, cancellation and recovery coordination

**Primary REQ:** `REQ-ARC-003`
**Task role:** **change owner**
**Dependencies:** `TASK-P03-014`, `TASK-P04-001`

### Implementation intent

Sequential execution, queue state, cooperative cancellation, restart coordination and primary-delivery outcome coordination SHALL be application-owned capabilities independent of Telegram transport mechanics.

**Current brownfield focus:** No specific brownfield defect is singled out; preserve approved behavior while establishing the required contract.

**Likely touchpoints:** Sequential execution/queue service, cooperative cancellation, startup coordination and primary-delivery outcome coordination behind application-owned interfaces.

**Integration note:** Keep Telegram queue presentation and message editing transport-specific; move lifecycle decisions only.

### Red

Create or strengthen the lowest useful tests that express the frozen acceptance boundary:

- AC-01: Queue behavior can be driven through application tests without Telegram classes.
- AC-02: Queue state mutations and Job lifecycle persistence remain coherent.
- AC-03: Cancellation token propagation is transport-independent.
- AC-04: Startup recovery consumes application request context and source-valid recoverability rules rather than Telegram payload objects.

If all acceptance criteria are already satisfied, record characterization evidence instead of manufacturing an artificial failing test. For host-only or environment-only criteria, a failing preflight/rehearsal criterion is valid Red evidence; do not fabricate a unit-test substitute.

### Green

Implement the minimum coherent change required to satisfy the failing acceptance evidence while preserving all upstream frozen behavior and the current plan ownership boundary.

### Refactor / convergence

Remove temporary duplication introduced by the migration, keep one owner for each policy/capability, and run relevant architecture/contract/conformance checks before considering the task complete.

### Completion evidence

- queue/cancellation application tests
- startup-recovery tests
- architecture tests

Also record the quality gates actually run and any environment-gated evidence deferred to PLAN-006.

## TASK-P04-003 — Extract completed-history selection and retrieval workflow

**Primary REQ:** none; supports frozen requirements without closing them
**Supports:** `REQ-ARC-002`
**Task role:** **support / foundation**
**Dependencies:** `TASK-P03-014`, `TASK-P04-001`

### Scope

Move completed-history ordering, positional selection and canonical-Markdown retrieval decisions from `infrastructure.telegram` into an application capability without merging them with textual search.

**Integration note:** Textual search is handled separately by TASK-P04-005/006/007.

### Red / characterization

Characterize `/list` and `/last` ordering/selection, operator scoping and missing-artifact behavior independently of Telegram rendering.

### Green

Create/move only the portable history selection/retrieval collaboration and make Telegram delegate to it. Keep formatting/buttons in the adapter.

### Refactor / convergence

Do not create a second source of policy truth. Remove temporary migration scaffolding when the owning closure task has replacement evidence.

### Completion evidence

- application history tests without Telegram classes;
- adapter delegation/conformance tests;
- no textual-search merge.

## TASK-P04-004 — Derived artifact association and authority

**Primary REQ:** `REQ-DATA-005`
**Task role:** **change owner**
**Dependencies:** `TASK-P03-014`

### Implementation intent

Derived artifacts SHALL be explicitly associated with their canonical transcript/Job identity, remain regenerable where practical, and SHALL never become an alternate source of transcript truth.

**Current brownfield focus:** No specific brownfield defect is singled out; preserve approved behavior while establishing the required contract.

**Likely touchpoints:** Derived-artifact metadata/association for summaries, exports and video derivatives without changing canonical transcript authority.

### Red

Create or strengthen the lowest useful tests that express the frozen acceptance boundary:

- AC-01: Summary, export and video derivative metadata identifies its canonical source association.
- AC-02: Regenerating a derived artifact does not mutate canonical transcript segments or provenance.
- AC-03: Deleting or failing to create a derivative does not invalidate an otherwise coherent canonical completed transcript.
- AC-04: Derived-artifact paths/metadata do not embed unrelated private staging information.

If all acceptance criteria are already satisfied, record characterization evidence instead of manufacturing an artificial failing test. For host-only or environment-only criteria, a failing preflight/rehearsal criterion is valid Red evidence; do not fabricate a unit-test substitute.

### Green

Implement the minimum coherent change required to satisfy the failing acceptance evidence while preserving all upstream frozen behavior and the current plan ownership boundary.

### Refactor / convergence

Remove temporary duplication introduced by the migration, keep one owner for each policy/capability, and run relevant architecture/contract/conformance checks before considering the task complete.

### Completion evidence

- derived-artifact linkage tests
- summary/export/video workflow tests

Also record the quality gates actually run and any environment-gated evidence deferred to PLAN-006.

## TASK-P04-005 — Textual-search index data and lifecycle

**Primary REQ:** `REQ-DATA-011`
**Task role:** **change owner**
**Dependencies:** `TASK-P03-014`, `TASK-P04-004`

### Implementation intent

Textual-search documents SHALL be treated as private derived data explicitly associated with completed canonical Jobs/transcripts and SHALL remain coherent with approved transcript/alias/summary changes.

**Current brownfield focus:** No specific brownfield defect is singled out; preserve approved behavior while establishing the required contract.

**Likely touchpoints:** Search-document schema/source fields, bounded FTS/fallback data, explicit refresh/rebuild semantics and privacy classification.

### Red

Create or strengthen the lowest useful tests that express the frozen acceptance boundary:

- AC-01: Search documents identify the canonical Job/transcript source without indexing private staging paths.
- AC-02: Deleting or making a Job non-searchable removes or invalidates its search document.
- AC-03: Speaker-alias and successful-summary changes refresh the affected textual-search state when those fields are part of the approved search document.
- AC-04: Search data is rebuildable from approved canonical/derived sources and is never alternate transcript truth.

If all acceptance criteria are already satisfied, record characterization evidence instead of manufacturing an artificial failing test. For host-only or environment-only criteria, a failing preflight/rehearsal criterion is valid Red evidence; do not fabricate a unit-test substitute.

### Green

Implement the minimum coherent change required to satisfy the failing acceptance evidence while preserving all upstream frozen behavior and the current plan ownership boundary.

### Refactor / convergence

Remove temporary duplication introduced by the migration, keep one owner for each policy/capability, and run relevant architecture/contract/conformance checks before considering the task complete.

### Completion evidence

- SQLite FTS/fallback integration tests
- rename/summary index-refresh tests
- search privacy tests

Also record the quality gates actually run and any environment-gated evidence deferred to PLAN-006.

## TASK-P04-006 — Separated lifecycle persistence, indexing and search capabilities

**Primary REQ:** `REQ-ARC-007`
**Task role:** **change owner**
**Dependencies:** `TASK-P03-014`, `TASK-P04-004`, `TASK-P04-005`

### Implementation intent

Lifecycle persistence, canonical transcript storage, indexing transformation and search query semantics SHALL be distinct application capabilities even when a temporary infrastructure class implements more than one interface.

**Current brownfield focus:** Current SQLAlchemy repository mixes lifecycle persistence, indexing/search and artifact loading.

**Likely touchpoints:** Job lifecycle repository, explicit indexer, search query capability and SQLite adapter interfaces/contract tests.

### Red

Create or strengthen the lowest useful tests that express the frozen acceptance boundary:

- AC-01: `JobRepository.save` has no hidden transcript/summary filesystem reads solely to update search state.
- AC-02: Index refresh is an explicit application-owned operation triggered by approved canonical/derived changes, not a hidden lifecycle-repository side effect.
- AC-03: Search capability may use FTS5 or the bounded fallback without changing lifecycle persistence semantics.
- AC-04: Contract/integration tests distinguish lifecycle persistence, indexing and search behavior.

If all acceptance criteria are already satisfied, record characterization evidence instead of manufacturing an artificial failing test. For host-only or environment-only criteria, a failing preflight/rehearsal criterion is valid Red evidence; do not fabricate a unit-test substitute.

### Green

Implement the minimum coherent change required to satisfy the failing acceptance evidence while preserving all upstream frozen behavior and the current plan ownership boundary.

### Refactor / convergence

Remove temporary duplication introduced by the migration, keep one owner for each policy/capability, and run relevant architecture/contract/conformance checks before considering the task complete.

### Completion evidence

- contract/integration tests for each capability
- SQLite FTS/fallback tests

Also record the quality gates actually run and any environment-gated evidence deferred to PLAN-006.

## TASK-P04-007 — Extract textual-search application workflow

**Primary REQ:** none; supports frozen requirements without closing them
**Supports:** `REQ-ARC-002`
**Task role:** **support / foundation**
**Dependencies:** `TASK-P03-014`, `TASK-P04-001`, `TASK-P04-006`

### Scope

Move query validation, completed/operator scope and result orchestration for textual search into application behavior that consumes the separated search capability. Preserve FTS5/fallback as infrastructure/data behavior and keep search separate from history browsing.

**Integration note:** This task supports `REQ-ARC-002`; `REQ-ARC-007` remains the sole owner of lifecycle/index/search capability separation.

### Red / characterization

Characterize `/search` query/result semantics, fallback behavior and sanitized snippets through application-facing tests.

### Green

Introduce/move the application search use case/service and make Telegram delegate presentation to it without moving SQL/FTS details into application.

### Refactor / convergence

Do not create a second source of policy truth. Remove temporary migration scaffolding when the owning closure task has replacement evidence.

### Completion evidence

- application search tests without Telegram classes;
- FTS/fallback contract tests remain green;
- adapter delegation tests.

## TASK-P04-008 — Extract transcript edit/export/video-derivative orchestration

**Primary REQ:** none; supports frozen requirements without closing them
**Supports:** `REQ-ARC-002`
**Task role:** **support / foundation**
**Dependencies:** `TASK-P03-014`, `TASK-P04-001`, `TASK-P04-004`, `TASK-P04-006`

### Scope

Move portable command orchestration for speaker rename/merge, transcript exports and YouTube video derivative selection out of Telegram while reusing the canonical transcript/derived-artifact capabilities already established. Keep Telegram-specific inline rename session presentation and send mechanics at the adapter.

**Integration note:** Functional acceptance remains in PLAN-005; this task changes ownership only.

### Red / characterization

Characterize rename/export/video command selection, history-position resolution and missing-evidence/error outcomes without coupling the new application tests to Telegram classes.

### Green

Create/move application use cases/services for these orchestration paths and make Telegram delegate. Do not duplicate canonical store, export rendering or video-provider policy.

### Refactor / convergence

Do not create a second source of policy truth. Remove temporary migration scaffolding when the owning closure task has replacement evidence.

### Completion evidence

- application rename/export/video orchestration tests;
- adapter delegation tests;
- canonical/derived artifact contracts remain single-source.

## TASK-P04-009 — Application summary policy and infrastructure text-generation transport

**Primary REQ:** `REQ-ARC-008`
**Task role:** **change owner**
**Dependencies:** `TASK-P03-014`

### Implementation intent

Summary transcript selection, chunking/reduction, prompt/output policy and application-level recovery decisions SHALL be application-owned, while HTTP/auth/provider translation and concrete tokenizer/model-library integration SHALL remain infrastructure implementations of narrow capabilities.

**Current brownfield focus:** No specific brownfield defect is singled out; preserve approved behavior while establishing the required contract.

**Likely touchpoints:** Summary application workflow/policy, tokenizer and text-generation capability interfaces, plus concrete HTTP/tokenizer adapters.

**Integration note:** Telegram may continue to present summary progress/results but must delegate portable summary policy to application.

### Red

Create or strengthen the lowest useful tests that express the frozen acceptance boundary:

- AC-01: Application summary workflow runs with fake canonical store, tokenizer and text-generation capability.
- AC-02: Network client contains no transcript-selection, chunking or summary-output business policy.
- AC-03: Application owns whether/how a failed or timed-out summary unit is subdivided/reduced; adapter owns the mechanism of an individual transport request and its transport timeout.
- AC-04: Text-generation capability is justified by current summarization needs and does not pre-specify translation semantics.

If all acceptance criteria are already satisfied, record characterization evidence instead of manufacturing an artificial failing test. For host-only or environment-only criteria, a failing preflight/rehearsal criterion is valid Red evidence; do not fabricate a unit-test substitute.

### Green

Implement the minimum coherent change required to satisfy the failing acceptance evidence while preserving all upstream frozen behavior and the current plan ownership boundary.

### Refactor / convergence

Remove temporary duplication introduced by the migration, keep one owner for each policy/capability, and run relevant architecture/contract/conformance checks before considering the task complete.

### Completion evidence

- application summary unit tests
- text-generation/tokenizer adapter contract tests
- architecture tests

Also record the quality gates actually run and any environment-gated evidence deferred to PLAN-006.

## TASK-P04-010 — Bounded private operational logs

**Primary REQ:** `REQ-DATA-006`
**Task role:** **change owner**
**Dependencies:** `TASK-P03-014`

### Implementation intent

Operational error, audit and application logs SHALL be private, sanitized, queryable for the approved diagnostic/evidence purpose, and subject to explicit bounded retention so recent-error inspection does not require unbounded accumulation.

**Current brownfield focus:** No specific brownfield defect is singled out; preserve approved behavior while establishing the required contract.

**Likely touchpoints:** Operational error/audit/log persistence format, bounded read/write/retention semantics and private classification.

### Red

Create or strengthen the lowest useful tests that express the frozen acceptance boundary:

- AC-01: Central operational logs have configured rotation, retention or compaction semantics.
- AC-02: `/lasterror` reads a bounded recent window and does not require loading indefinitely growing history.
- AC-03: Audit records omit transcript, prompt and provider payload bodies except for separately approved local-debug behavior.
- AC-04: Readiness evidence that must outlive ordinary log retention is stored/retained under its explicit evidence policy rather than relying on accidental log survival.

If all acceptance criteria are already satisfied, record characterization evidence instead of manufacturing an artificial failing test. For host-only or environment-only criteria, a failing preflight/rehearsal criterion is valid Red evidence; do not fabricate a unit-test substitute.

### Green

Implement the minimum coherent change required to satisfy the failing acceptance evidence while preserving all upstream frozen behavior and the current plan ownership boundary.

### Refactor / convergence

Remove temporary duplication introduced by the migration, keep one owner for each policy/capability, and run relevant architecture/contract/conformance checks before considering the task complete.

### Completion evidence

- log-retention tests
- bounded-read tests
- sanitization tests
- evidence-storage review

Also record the quality gates actually run and any environment-gated evidence deferred to PLAN-006.

## TASK-P04-011 — Reconstructible cache lifecycle

**Primary REQ:** `REQ-DATA-007`
**Task role:** **change owner**
**Dependencies:** `TASK-P03-014`

### Implementation intent

Model, tokenizer and other cache data classified as reconstructible SHALL have explicit owned scope and safe cleanup semantics independent of canonical transcript retention.

**Current brownfield focus:** No specific brownfield defect is singled out; preserve approved behavior while establishing the required contract.

**Likely touchpoints:** Owned model/tokenizer/cache roots, availability metadata and safe reconstructible-cache cleanup semantics.

### Red

Create or strengthen the lowest useful tests that express the frozen acceptance boundary:

- AC-01: Cache roots are explicitly configured or otherwise deterministically owned by the application.
- AC-02: Clearing cache never deletes Job DB, transcript snapshots, Markdown, summaries, credentials or unrelated data.
- AC-03: Subsequent approved processing may rebuild or redownload reconstructible cache.
- AC-04: Cache cleanup does not modify the configured model/tokenizer trust policy.

If all acceptance criteria are already satisfied, record characterization evidence instead of manufacturing an artificial failing test. For host-only or environment-only criteria, a failing preflight/rehearsal criterion is valid Red evidence; do not fabricate a unit-test substitute.

### Green

Implement the minimum coherent change required to satisfy the failing acceptance evidence while preserving all upstream frozen behavior and the current plan ownership boundary.

### Refactor / convergence

Remove temporary duplication introduced by the migration, keep one owner for each policy/capability, and run relevant architecture/contract/conformance checks before considering the task complete.

### Completion evidence

- cache containment/deletion tests
- configuration conformance tests

Also record the quality gates actually run and any environment-gated evidence deferred to PLAN-006.

## TASK-P04-012 — Operational policy separated from external I/O mechanisms

**Primary REQ:** `REQ-ARC-009`
**Task role:** **change owner**
**Dependencies:** `TASK-P03-014`, `TASK-P04-010`, `TASK-P04-011`

### Implementation intent

Health, error-selection, retention and related operational policy SHALL remain application behavior while filesystem, network, subprocess and log mechanisms are accessed through explicit purpose-specific probes/stores/adapters rather than direct external I/O in application policy code.

**Current brownfield focus:** No specific brownfield defect is singled out; preserve approved behavior while establishing the required contract.

**Likely touchpoints:** Health probes, operational-error store, retention deletion capability and cache/storage mechanisms behind application-owned operational policy.

**Integration note:** Reuse PLAN-001 path containment/sanitization; do not create new generic filesystem or probe buses.

### Red

Create or strengthen the lowest useful tests that express the frozen acceptance boundary:

- AC-01: Healthcheck application logic consumes injected probe results/capabilities.
- AC-02: Operational-error persistence is behind a purpose-specific application-owned store/capability.
- AC-03: Retention requests deletion through owned artifact/storage capabilities.
- AC-04: Using stdlib filesystem/network/subprocess APIs directly does not bypass the application/infrastructure boundary.

If all acceptance criteria are already satisfied, record characterization evidence instead of manufacturing an artificial failing test. For host-only or environment-only criteria, a failing preflight/rehearsal criterion is valid Red evidence; do not fabricate a unit-test substitute.

### Green

Implement the minimum coherent change required to satisfy the failing acceptance evidence while preserving all upstream frozen behavior and the current plan ownership boundary.

### Refactor / convergence

Remove temporary duplication introduced by the migration, keep one owner for each policy/capability, and run relevant architecture/contract/conformance checks before considering the task complete.

### Completion evidence

- architecture tests for application I/O hotspots
- application tests with fake probes/stores

Also record the quality gates actually run and any environment-gated evidence deferred to PLAN-006.

## TASK-P04-013 — Extract operational command orchestration and retention invocation

**Primary REQ:** none; supports frozen requirements without closing them
**Supports:** `REQ-ARC-002`
**Task role:** **support / foundation**
**Dependencies:** `TASK-P03-014`, `TASK-P04-001`, `TASK-P04-011`, `TASK-P04-012`

### Scope

Move portable orchestration for healthcheck, last-error selection, cache clearing and retention invocation out of Telegram/direct infrastructure collaborators, while keeping Telegram command parsing/presentation and host-specific I/O in adapters.

**Integration note:** This task supports `REQ-ARC-002`; automatic host execution/rehearsal remains PLAN-006.

### Red / characterization

Characterize current `/healthcheck`, `/lasterror`, `/clearcache` and automatic-retention invocation semantics through application-facing fakes/probes/stores.

### Green

Introduce/move the minimal application use cases/services that coordinate the operational policies from TASK-P04-012 and make Telegram/runtime wiring delegate to them.

### Refactor / convergence

Do not create a second source of policy truth. Remove temporary migration scaffolding when the owning closure task has replacement evidence.

### Completion evidence

- operational application tests with fake probes/stores;
- adapter/runtime delegation tests;
- no direct filesystem/network/subprocess I/O in application policy.

## TASK-P04-014 — Application workflow ownership and thin Telegram transport

**Primary REQ:** `REQ-ARC-002`
**Task role:** **closure owner**
**Dependencies:** `TASK-P03-014`, `TASK-P04-001`, `TASK-P04-002`, `TASK-P04-003`, `TASK-P04-006`, `TASK-P04-007`, `TASK-P04-008`, `TASK-P04-009`, `TASK-P04-012`, `TASK-P04-013`

### Implementation intent

Portable workflow decisions SHALL be owned by application use cases/services while Telegram infrastructure is limited to Telegram protocol parsing/presentation, Telegram-specific inline state, boundary authorization/audience enforcement and send mechanics.

**Current brownfield focus:** `TelegramBotAdapter` and `HistoryCollaboration` currently own substantial application policy.

**Likely touchpoints:** Telegram adapter dependency graph, portable application use cases/services and architecture/import/conformance tests.

### Red

Create or strengthen the lowest useful tests that express the frozen acceptance boundary:

- AC-01: Submission/dedup/cancel/history/search/rename/summary/export/retention/delivery-result policy can be exercised without Telegram classes.
- AC-02: Telegram callback/UI state that has no portable business meaning may remain in the adapter.
- AC-03: History selection rules are not owned solely by `infrastructure.telegram`.
- AC-04: Telegram adapter dependencies are application capabilities/use cases rather than a parallel concrete service graph.

If all acceptance criteria are already satisfied, record characterization evidence instead of manufacturing an artificial failing test. For host-only or environment-only criteria, a failing preflight/rehearsal criterion is valid Red evidence; do not fabricate a unit-test substitute.

### Green

Treat this as the thin-transport closure task. Verify the full frozen acceptance boundary after the workflow-specific extraction tasks. Do not reimplement submission, execution, history/search, summary, derivative or operational policy here; route any failure to the corresponding owner. Implement only residual adapter-dependency cleanup uniquely needed to leave Telegram as protocol/presentation/UI-state/send mechanics.

### Refactor / convergence

Remove temporary duplication introduced by the migration, keep one owner for each policy/capability, and run relevant architecture/contract/conformance checks before considering the task complete.

### Completion evidence

- application tests without Telegram classes
- architecture/import tests
- adapter conformance tests

Also record the quality gates actually run and any environment-gated evidence deferred to PLAN-006.

## TASK-P04-015 — Deterministic lifecycle reliability and failure isolation

**Primary REQ:** `REQ-NFR-001`
**Task role:** **assurance owner**
**Dependencies:** `TASK-P03-014`, `TASK-P04-002`, `TASK-P04-009`, `TASK-P04-012`, `TASK-P04-014`

### Implementation intent

Equivalent lifecycle events SHALL produce deterministic valid outcomes, failures in derived or diagnostic operations SHALL remain isolated from canonical completed Jobs, and repeatable recovery actions SHALL be idempotent where repeated execution is possible.

**Current brownfield focus:** No specific brownfield defect is singled out; preserve approved behavior while establishing the required contract.

**Likely touchpoints:** Lifecycle/state/restart idempotency, derived-operation failure isolation and canonical-completion regression suites.

### Red

Create or strengthen the lowest useful tests that express the frozen acceptance boundary:

- AC-01: Invalid lifecycle transitions fail deterministically.
- AC-02: Repeated startup reconciliation does not repeatedly mutate already reconciled terminal state.
- AC-03: Failure of a derived/diagnostic operation does not retroactively mutate a canonical completed Job.
- AC-04: Canonical persistence failure cannot be reported as successful completion.

If all acceptance criteria are already satisfied, record characterization evidence instead of manufacturing an artificial failing test. For host-only or environment-only criteria, a failing preflight/rehearsal criterion is valid Red evidence; do not fabricate a unit-test substitute.

### Green

This is a cross-cutting assurance task. Run the frozen reliability criteria across the already-migrated components. If a failure belongs to lifecycle/canonical semantics from PLAN-002 or an application workflow from earlier PLAN-004 tasks, reopen that owner rather than adding a parallel fix here. Implement here only residual cross-cutting idempotency/failure-isolation behavior not owned elsewhere.

### Refactor / convergence

Remove temporary duplication introduced by the migration, keep one owner for each policy/capability, and run relevant architecture/contract/conformance checks before considering the task complete.

### Completion evidence

- lifecycle/state-machine tests
- restart idempotency tests
- derived-failure isolation tests

Also record the quality gates actually run and any environment-gated evidence deferred to PLAN-006.

## TASK-P04-016 — Cohesive, testable and reversible baseline refactoring

**Primary REQ:** `REQ-NFR-005`
**Task role:** **assurance / convergence owner**
**Dependencies:** `TASK-P03-014`, `TASK-P04-001`, `TASK-P04-002`, `TASK-P04-003`, `TASK-P04-004`, `TASK-P04-005`, `TASK-P04-006`, `TASK-P04-007`, `TASK-P04-008`, `TASK-P04-009`, `TASK-P04-010`, `TASK-P04-011`, `TASK-P04-012`, `TASK-P04-013`, `TASK-P04-014`, `TASK-P04-015`

### Implementation intent

Baseline repair SHALL reduce responsibility hotspots through small reversible changes protected by characterization, contract, architecture and regression tests, and SHALL not preserve or add abstractions without a demonstrated approved capability.

**Current brownfield focus:** No specific brownfield defect is singled out; preserve approved behavior while establishing the required contract.

**Likely touchpoints:** Hotspot decomposition, characterization coverage, obsolete empty/speculative packages and reviewable change boundaries.

### Red

Create or strengthen the lowest useful tests that express the frozen acceptance boundary:

- AC-01: Telegram, summary and persistence hotspots are decomposed according to responsibility/contract rather than file size alone.
- AC-02: Empty speculative domain packages are removed unless a current approved contract requires them.
- AC-03: Generic `FileStorage` disappears when explicit replacement-capability coverage exists.
- AC-04: Refactors preserve frozen behavior unless an approved requirement classifies the current behavior as a defect or authorized hardening.

If all acceptance criteria are already satisfied, record characterization evidence instead of manufacturing an artificial failing test. For host-only or environment-only criteria, a failing preflight/rehearsal criterion is valid Red evidence; do not fabricate a unit-test substitute.

### Green

This is the final PLAN-004 convergence/assurance task. Remove only demonstrably unused empty/speculative package surfaces and migration scaffolding still left after consumers moved. Verify that generic `FileStorage` was already removed by TASK-P03-011; if it was not, reopen that task instead of duplicating the cleanup. Do not initiate another broad refactor here.

### Refactor / convergence

Remove temporary duplication introduced by the migration, keep one owner for each policy/capability, and run relevant architecture/contract/conformance checks before considering the task complete.

### Completion evidence

- characterization/contract tests before affected refactors
- architecture tests
- reviewable incremental diffs

Also record the quality gates actually run and any environment-gated evidence deferred to PLAN-006.

## TASK-P04-017 — PLAN-004 exit-gate verification

**Primary REQ:** none; plan gate
**Task role:** **plan gate**
**Dependencies:** `TASK-P04-001`, `TASK-P04-002`, `TASK-P04-003`, `TASK-P04-004`, `TASK-P04-005`, `TASK-P04-006`, `TASK-P04-007`, `TASK-P04-008`, `TASK-P04-009`, `TASK-P04-010`, `TASK-P04-011`, `TASK-P04-012`, `TASK-P04-013`, `TASK-P04-014`, `TASK-P04-015`, `TASK-P04-016`

### Scope

Verify that every primary owner, support/foundation task and assurance task in PLAN-004 satisfies the frozen plan exit gate before work in the next plan is treated as implementation-ready. This task does not add product behavior or reimplement a failed criterion.

### Gate evidence

- Portable application workflows execute without Telegram classes.
- Lifecycle repository tests no longer require hidden search-index side effects.
- FTS/fallback integration tests remain green through the split.
- Summary application tests run with fake text generation/tokenizer/store.
- Operational application tests use fake probes/stores and contain no direct infrastructure imports or direct filesystem/network/subprocess operations.
- Telegram adapter responsibility is materially reduced and no new god-object replaces it.
- Refactors are covered by characterization/contract/architecture evidence and remain reversible at plan-sized increments.

### Completion rule

Record commands/evidence, unresolved environment limitations and any failed criterion. A failed criterion MUST be routed to the task that owns the missing behavior or evidence; the gate itself does not patch around the failure. Shared operational evidence may be referenced rather than rerun when it was captured on the same closure revision and remains valid.
