# PLAN-002 Tasks — Domain truth, canonical data and compatibility migration

Version: **1.0.0**
Status: **Approved / Frozen**
Derived from: **004-planning v1.0.0 (Approved / Frozen)**

## Execution rule

Domain/data migrations are executed in dependency order with legacy round-trip evidence before destructive cleanup. `TASK-P02-012` is a compatibility assurance owner: it verifies the combined migration and routes failures back to the task that owns the affected representation instead of layering duplicate shims.

## TASK-P02-001 — Source-neutral media identity

**Primary REQ:** `REQ-DOM-001`
**Task role:** **change owner**
**Dependencies:** `TASK-P01-008`

### Implementation intent

The domain SHALL represent media identity by source type plus a source-appropriate canonical identity without inventing YouTube identity for non-YouTube media or conflating identity with acquisition location.

**Current brownfield focus:** No specific brownfield defect is singled out; preserve approved behavior while establishing the required contract.

**Likely touchpoints:** `MediaSource`, Job construction, source acquisition and source-neutral metadata terminology.

### Red

Create or strengthen the lowest useful tests that express the frozen acceptance boundary:

- AC-01: YouTube identity retains video_id/canonical-URL semantics.
- AC-02: Telegram audio has a distinct private source identity and no synthetic video_id.
- AC-03: A local staging/download path is not the canonical media identity.
- AC-04: Internal generic-media names are source-neutral; source-specific names remain only for genuinely source-specific concepts.

If all acceptance criteria are already satisfied, record characterization evidence instead of manufacturing an artificial failing test. For host-only or environment-only criteria, a failing preflight/rehearsal criterion is valid Red evidence; do not fabricate a unit-test substitute.

### Green

Implement the minimum coherent change required to satisfy the failing acceptance evidence while preserving all upstream frozen behavior and the current plan ownership boundary.

### Refactor / convergence

Remove temporary duplication introduced by the migration, keep one owner for the policy/capability, and run relevant architecture/contract/conformance checks before considering the task complete.

### Completion evidence

- domain unit tests
- persistence round-trip compatibility tests

Also record the quality gates actually run and any environment-gated evidence deferred to PLAN-006.

## TASK-P02-002 — Explicit Job lifecycle state machine

**Primary REQ:** `REQ-DOM-002`
**Task role:** **change owner**
**Dependencies:** `TASK-P01-008`, `TASK-P02-001`

### Implementation intent

`Job` SHALL enforce the approved semantic transition graph and terminal-state rules, rejecting impossible transitions rather than permitting arbitrary non-terminal state changes.

**Current brownfield focus:** Current `Job.transition_to` only prevents leaving terminal states.

**Likely touchpoints:** `domain/entities/job.py`, pipeline state transitions, delivery transitions and startup-recovery tests.

### Red

Create or strengthen the lowest useful tests that express the frozen acceptance boundary:

- AC-01: Legal normal path includes pending→acquiring→converting→transcribing→diarizing→rendering→delivering→completed, with the approved subtitle shortcut acquiring→rendering.
- AC-02: Cancellation is legal only in approved pre-delivery processing states.
- AC-03: `completed`, `delivery_failed`, `failed` and `cancelled` are terminal.
- AC-04: Same-state assignment is not treated as a semantic transition.
- AC-05: Legacy persisted `downloading` is decoded as semantic `acquiring` without destructive migration.

If all acceptance criteria are already satisfied, record characterization evidence instead of manufacturing an artificial failing test. For host-only or environment-only criteria, a failing preflight/rehearsal criterion is valid Red evidence; do not fabricate a unit-test substitute.

### Green

Implement the minimum coherent change required to satisfy the failing acceptance evidence while preserving all upstream frozen behavior and the current plan ownership boundary.

### Refactor / convergence

Remove temporary duplication introduced by the migration, keep one owner for the policy/capability, and run relevant architecture/contract/conformance checks before considering the task complete.

### Completion evidence

- parameterized legal/illegal transition tests
- persistence compatibility tests

Also record the quality gates actually run and any environment-gated evidence deferred to PLAN-006.

## TASK-P02-003 — Truthful transcript and language semantics

**Primary REQ:** `REQ-DOM-003`
**Task role:** **change owner**
**Dependencies:** `TASK-P01-008`

### Implementation intent

Canonical Transcript SHALL preserve truthful segment, speaker, language, language-source and confidence semantics; unknown, forced and independently observed facts SHALL remain distinguishable and SHALL not be fabricated or silently relabeled.

**Current brownfield focus:** WhisperX currently maps unsupported detected language to `allowed_languages[0]`; YouTube metadata defaults an unknown language to English.

**Likely touchpoints:** Transcript/language value semantics, pipeline context, YouTube metadata inference and WhisperX language result mapping.

### Red

Create or strengthen the lowest useful tests that express the frozen acceptance boundary:

- AC-01: Segments require non-empty text and a positive time span.
- AC-02: Source/transcript language may remain unknown until a truthful source exists.
- AC-03: An independently ASR-observed language outside the allowlist is never rewritten as another allowed language.
- AC-04: An operator-requested/forced language constraint is distinguishable from an independently observed language and from the confidence of that observation.
- AC-05: When forced decoding provides no independent confidence for the forced language, canonical evidence records confidence as unknown/not-provided rather than borrowing an unrelated score.
- AC-06: Subtitle-derived transcripts record subtitle provenance distinctly from ASR-derived transcripts.

If all acceptance criteria are already satisfied, record characterization evidence instead of manufacturing an artificial failing test. For host-only or environment-only criteria, a failing preflight/rehearsal criterion is valid Red evidence; do not fabricate a unit-test substitute.

### Green

Implement the minimum coherent change required to satisfy the failing acceptance evidence while preserving all upstream frozen behavior and the current plan ownership boundary.

### Refactor / convergence

Remove temporary duplication introduced by the migration, keep one owner for the policy/capability, and run relevant architecture/contract/conformance checks before considering the task complete.

### Completion evidence

- domain invariant tests
- ASR/subtitle forced-language regression tests

Also record the quality gates actually run and any environment-gated evidence deferred to PLAN-006.

## TASK-P02-004 — Canonical and derived artifact taxonomy

**Primary REQ:** `REQ-DOM-004`
**Task role:** **change owner**
**Dependencies:** `TASK-P01-008`, `TASK-P02-003`

### Implementation intent

The system SHALL maintain an explicit artifact taxonomy distinguishing canonical machine-readable transcript evidence, canonical human-readable Markdown, derived artifacts, volatile media, operational data and reconstructible cache so lifecycle actions cannot silently change artifact authority.

**Current brownfield focus:** No specific brownfield defect is singled out; preserve approved behavior while establishing the required contract.

**Likely touchpoints:** Artifact classification used by transcript, derived artifacts, retention, cache and operational data.

### Red

Create or strengthen the lowest useful tests that express the frozen acceptance boundary:

- AC-01: The versioned structured transcript is canonical machine-readable evidence.
- AC-02: Markdown is the canonical human-readable rendering of that structured evidence.
- AC-03: Summary/export/search/video outputs are derived and never become alternate transcript truth.
- AC-04: Volatile media and reconstructible cache may be removed only under their explicit lifecycle policy.

If all acceptance criteria are already satisfied, record characterization evidence instead of manufacturing an artificial failing test. For host-only or environment-only criteria, a failing preflight/rehearsal criterion is valid Red evidence; do not fabricate a unit-test substitute.

### Green

Implement the minimum coherent change required to satisfy the failing acceptance evidence while preserving all upstream frozen behavior and the current plan ownership boundary.

### Refactor / convergence

Remove temporary duplication introduced by the migration, keep one owner for the policy/capability, and run relevant architecture/contract/conformance checks before considering the task complete.

### Completion evidence

- artifact-classification conformance tests
- traceability review

Also record the quality gates actually run and any environment-gated evidence deferred to PLAN-006.

## TASK-P02-005 — Versioned processing fingerprint and run provenance

**Primary REQ:** `REQ-DOM-005`
**Task role:** **change owner**
**Dependencies:** `TASK-P01-008`, `TASK-P02-001`, `TASK-P02-002`, `TASK-P02-003`

### Implementation intent

The system SHALL maintain one versioned processing-fingerprint concept for request-time policy that can materially affect canonical transcript production, and SHALL separately retain known actual run provenance describing the path/providers actually used.

**Current brownfield focus:** Current configuration-signature mechanisms overlap and current snapshot provenance is incomplete.

**Likely touchpoints:** `config_signature.py`, AppSettings fingerprint logic and actual run provenance carried into canonical evidence.

### Red

Create or strengthen the lowest useful tests that express the frozen acceptance boundary:

- AC-01: Fingerprint excludes credentials, local paths, chat/user IDs, retention/log settings and unrelated operational values.
- AC-02: Fingerprint schema defines result-significant source-selection, audio, ASR, language, diarization and normalization policy that could affect the request's canonical result, including configured fallback policy even when a particular branch is not exercised.
- AC-03: Known actual source path, subtitle/ASR choice, backend/model/runtime and diarization/fallback facts are recorded as run provenance rather than silently inferred from fingerprint identity.
- AC-04: Historical missing provenance is represented as unknown/not-recorded.
- AC-05: Only one canonical fingerprint field-set/owner remains.

If all acceptance criteria are already satisfied, record characterization evidence instead of manufacturing an artificial failing test. For host-only or environment-only criteria, a failing preflight/rehearsal criterion is valid Red evidence; do not fabricate a unit-test substitute.

### Green

Implement the minimum coherent change required to satisfy the failing acceptance evidence while preserving all upstream frozen behavior and the current plan ownership boundary.

### Refactor / convergence

Remove temporary duplication introduced by the migration, keep one owner for the policy/capability, and run relevant architecture/contract/conformance checks before considering the task complete.

### Completion evidence

- determinism tests
- config-field inclusion/exclusion tests
- snapshot/job provenance tests

Also record the quality gates actually run and any environment-gated evidence deferred to PLAN-006.

## TASK-P02-006 — Volatile media ownership and lifecycle

**Primary REQ:** `REQ-DATA-002`
**Task role:** **change owner**
**Dependencies:** `TASK-P01-008`, `TASK-P02-001`, `TASK-P02-004`

### Implementation intent

Staged, downloaded and converted media SHALL have explicit ownership, validity and cleanup semantics across validation rejection, cancellation, processing failure and restart.

**Current brownfield focus:** No specific brownfield defect is singled out; preserve approved behavior while establishing the required contract.

**Likely touchpoints:** Telegram staging paths, YouTube/downloaded media, converted audio, cancellation/failure cleanup and restart behavior.

### Red

Create or strengthen the lowest useful tests that express the frozen acceptance boundary:

- AC-01: Rejected or cancelled Telegram staging is removed when no longer required for an approved recovery path.
- AC-02: Unknown duration is represented as unknown, not zero, and is resolved by a bounded source-appropriate mechanism before expensive ASR/diarization or the request is rejected.
- AC-03: Temporary acquisition/conversion outputs are associated with the owning Job/request context rather than selected by arbitrary directory age.
- AC-04: Cleanup never removes canonical transcript evidence or media owned by unrelated work.

If all acceptance criteria are already satisfied, record characterization evidence instead of manufacturing an artificial failing test. For host-only or environment-only criteria, a failing preflight/rehearsal criterion is valid Red evidence; do not fabricate a unit-test substitute.

### Green

Implement the minimum coherent change required to satisfy the failing acceptance evidence while preserving all upstream frozen behavior and the current plan ownership boundary.

### Refactor / convergence

Remove temporary duplication introduced by the migration, keep one owner for the policy/capability, and run relevant architecture/contract/conformance checks before considering the task complete.

### Completion evidence

- media lifecycle unit/integration tests
- ffmpeg-gated evidence
- cancellation/rejection cleanup tests

Also record the quality gates actually run and any environment-gated evidence deferred to PLAN-006.

## TASK-P02-007 — Durable Job state and restart/delivery request context

**Primary REQ:** `REQ-DATA-001`
**Task role:** **change owner**
**Dependencies:** `TASK-P01-008`, `TASK-P02-002`, `TASK-P02-005`

### Implementation intent

Persistence SHALL durably associate each Job with the minimum source/request/provenance/routing state needed for history and restart/delivery semantics while keeping transport-specific routing outside the pure Job domain model.

**Current brownfield focus:** `Job` currently contains `requested_chat_id` and overloads `source_url` for URL/local-path semantics.

**Likely touchpoints:** Job persistence schema/repository plus application-owned request/delivery routing context compatible with historical columns.

### Red

Create or strengthen the lowest useful tests that express the frozen acceptance boundary:

- AC-01: Job identity, lifecycle and recorded provenance survive restart.
- AC-02: Source recovery data is source-specific; a non-empty string alone is not sufficient proof of recoverability.
- AC-03: Telegram chat routing may be persisted as application request/delivery context but is not an intrinsic pure-domain Job property.
- AC-04: No full Telegram/provider payload is persisted merely as restart state.

If all acceptance criteria are already satisfied, record characterization evidence instead of manufacturing an artificial failing test. For host-only or environment-only criteria, a failing preflight/rehearsal criterion is valid Red evidence; do not fabricate a unit-test substitute.

### Green

Implement the minimum coherent change required to satisfy the failing acceptance evidence while preserving all upstream frozen behavior and the current plan ownership boundary.

### Refactor / convergence

Remove temporary duplication introduced by the migration, keep one owner for the policy/capability, and run relevant architecture/contract/conformance checks before considering the task complete.

### Completion evidence

- SQLite round-trip/migration integration tests
- startup recovery tests
- architecture test for domain transport leakage

Also record the quality gates actually run and any environment-gated evidence deferred to PLAN-006.

## TASK-P02-008 — Dual canonical transcript persistence and explicit linkage

**Primary REQ:** `REQ-DATA-003`
**Task role:** **change owner**
**Dependencies:** `TASK-P01-008`, `TASK-P02-003`, `TASK-P02-004`, `TASK-P02-005`

### Implementation intent

A successful transcript SHALL persist a versioned structured snapshot and its canonical Markdown rendering from the same logical Transcript, and the durable Job/application record SHALL have an explicit association with the canonical structured evidence.

**Current brownfield focus:** Current Job→snapshot linkage is inferred from Markdown slug/path convention.

**Likely touchpoints:** Transcript snapshot persistence, Markdown rendering and an explicit durable canonical transcript association.

### Red

Create or strengthen the lowest useful tests that express the frozen acceptance boundary:

- AC-01: New structured writes carry an explicit schema version.
- AC-02: Existing snapshot schema v1 remains readable.
- AC-03: Telegram evidence does not invent YouTube identity.
- AC-04: New persistence does not rely solely on `md_path` stem/slug to discover the canonical structured snapshot.
- AC-05: Structured consumers load structured evidence rather than parse Markdown when structured evidence exists.

If all acceptance criteria are already satisfied, record characterization evidence instead of manufacturing an artificial failing test. For host-only or environment-only criteria, a failing preflight/rehearsal criterion is valid Red evidence; do not fabricate a unit-test substitute.

### Green

Implement the minimum coherent change required to satisfy the failing acceptance evidence while preserving all upstream frozen behavior and the current plan ownership boundary.

### Refactor / convergence

Remove temporary duplication introduced by the migration, keep one owner for the policy/capability, and run relevant architecture/contract/conformance checks before considering the task complete.

### Completion evidence

- snapshot round-trip/legacy tests
- explicit-link persistence tests
- rename/export/summary contract tests

Also record the quality gates actually run and any environment-gated evidence deferred to PLAN-006.

## TASK-P02-009 — Backward-compatible persisted representations and migrations

**Primary REQ:** `REQ-DATA-008`
**Task role:** **change owner**
**Dependencies:** `TASK-P01-008`, `TASK-P02-007`, `TASK-P02-008`

### Implementation intent

Persistence and schema changes during baseline repair SHALL preserve readable historical Jobs/snapshots and use explicit tested migration or compatibility decoding instead of silent destructive rewriting.

**Current brownfield focus:** No specific brownfield defect is singled out; preserve approved behavior while establishing the required contract.

**Likely touchpoints:** SQLAlchemy schema/migration/compatibility decoding and snapshot schema-v1 fixtures.

### Red

Create or strengthen the lowest useful tests that express the frozen acceptance boundary:

- AC-01: Legacy `downloading` status remains readable as semantic `acquiring`.
- AC-02: Snapshot schema v1 remains readable.
- AC-03: Nullable/non-YouTube `video_id` semantics remain compatible.
- AC-04: Migration or compatibility decoding preserves segments, timestamps, speaker labels, source metadata and current re-renderability.
- AC-05: Any destructive migration requires explicit backup/rollback evidence before deployment.

If all acceptance criteria are already satisfied, record characterization evidence instead of manufacturing an artificial failing test. For host-only or environment-only criteria, a failing preflight/rehearsal criterion is valid Red evidence; do not fabricate a unit-test substitute.

### Green

Implement the minimum coherent change required to satisfy the failing acceptance evidence while preserving all upstream frozen behavior and the current plan ownership boundary.

### Refactor / convergence

Remove temporary duplication introduced by the migration, keep one owner for the policy/capability, and run relevant architecture/contract/conformance checks before considering the task complete.

### Completion evidence

- representative legacy SQLite integration tests
- snapshot compatibility tests
- migration/rollback tests

Also record the quality gates actually run and any environment-gated evidence deferred to PLAN-006.

## TASK-P02-010 — Completed-Job retention policy and canonical preservation

**Primary REQ:** `REQ-DATA-010`
**Task role:** **change owner**
**Dependencies:** `TASK-P01-008`, `TASK-P02-006`, `TASK-P02-008`

### Implementation intent

Completed-Job retention SHALL classify which artifact classes are eligible for automatic removal and SHALL preserve the canonical structured transcript and Markdown required by approved baseline history, rename and export behavior.

**Current brownfield focus:** No specific brownfield defect is singled out; preserve approved behavior while establishing the required contract.

**Likely touchpoints:** Completed-Job retention classification and canonical preservation.

### Red

Create or strengthen the lowest useful tests that express the frozen acceptance boundary:

- AC-01: The configured retention count/policy selects eligible completed Jobs deterministically.
- AC-02: Canonical structured snapshot and Markdown are not removed by completed-Job volatile retention.
- AC-03: Only artifact classes explicitly classified as volatile/retention-eligible are removed.
- AC-04: Retention eligibility is based on Job/artifact ownership and policy, not arbitrary unrelated filesystem age.

If all acceptance criteria are already satisfied, record characterization evidence instead of manufacturing an artificial failing test. For host-only or environment-only criteria, a failing preflight/rehearsal criterion is valid Red evidence; do not fabricate a unit-test substitute.

### Green

Implement the minimum coherent change required to satisfy the failing acceptance evidence while preserving all upstream frozen behavior and the current plan ownership boundary.

### Refactor / convergence

Remove temporary duplication introduced by the migration, keep one owner for the policy/capability, and run relevant architecture/contract/conformance checks before considering the task complete.

### Completion evidence

- retention policy tests
- artifact-classification conformance tests

Also record the quality gates actually run and any environment-gated evidence deferred to PLAN-006.

## TASK-P02-011 — Canonical completion consistency and artifact-reference truth

**Primary REQ:** `REQ-DATA-004`
**Task role:** **change owner**
**Dependencies:** `TASK-P01-008`, `TASK-P02-006`, `TASK-P02-007`, `TASK-P02-008`, `TASK-P02-010`

### Implementation intent

The system SHALL not advance a Job toward successful primary delivery/completion unless required canonical evidence is durably coherent, and durable metadata SHALL never claim an artifact is available after it was not created, became unreadable, or was deleted.

**Current brownfield focus:** `RenderMarkdownStep` currently swallows snapshot-save failure; retention can leave stale Job paths.

**Likely touchpoints:** Render/persist/delivery handoff, canonical write failures and durable artifact availability references.

### Red

Create or strengthen the lowest useful tests that express the frozen acceptance boundary:

- AC-01: Structured-snapshot persistence failure prevents successful transcript completion.
- AC-02: A partial canonical-write failure has an explicit failure outcome and does not leave lifecycle/reference metadata claiming successful canonical completion.
- AC-03: Retention and cleanup clear or truthfully mark references to removed artifacts.
- AC-04: Missing or corrupt required canonical evidence causes an explicit derived/history failure rather than silent reconstruction from Markdown or media.

If all acceptance criteria are already satisfied, record characterization evidence instead of manufacturing an artificial failing test. For host-only or environment-only criteria, a failing preflight/rehearsal criterion is valid Red evidence; do not fabricate a unit-test substitute.

### Green

Implement the minimum coherent change required to satisfy the failing acceptance evidence while preserving all upstream frozen behavior and the current plan ownership boundary.

### Refactor / convergence

Remove temporary duplication introduced by the migration, keep one owner for the policy/capability, and run relevant architecture/contract/conformance checks before considering the task complete.

### Completion evidence

- failure-injection tests for snapshot/Markdown writes
- retention reference tests
- corruption/missing-evidence tests

Also record the quality gates actually run and any environment-gated evidence deferred to PLAN-006.

## TASK-P02-012 — External behavior and data compatibility during baseline repair

**Primary REQ:** `REQ-NFR-006`
**Task role:** **assurance owner**
**Dependencies:** `TASK-P01-008`, `TASK-P02-009`

### Implementation intent

Baseline repair SHALL preserve frozen commands, aliases, approved operator configuration and readable historical data unless an approved versioned requirement explicitly changes an unsupported or unsafe surface.

**Current brownfield focus:** No specific brownfield defect is singled out; preserve approved behavior while establishing the required contract.

**Likely touchpoints:** Conformance fixtures for commands/aliases/env names/persisted data and migration compatibility.

**Integration note:** This task closes cross-cutting compatibility; it does not become a second owner of each migrated schema/domain behavior.

### Red

Create or strengthen the lowest useful tests that express the frozen acceptance boundary:

- AC-01: Existing approved environment variables remain accepted.
- AC-02: Legacy DB and snapshot data remain readable.
- AC-03: Frozen command aliases remain registered.
- AC-04: Internal Python names may change without public compatibility promise.
- AC-05: The private-chat-only hardening is documented as an intentional narrowing of an otherwise unspecified group/shared-chat surface.

If all acceptance criteria are already satisfied, record characterization evidence instead of manufacturing an artificial failing test. For host-only or environment-only criteria, a failing preflight/rehearsal criterion is valid Red evidence; do not fabricate a unit-test substitute.

### Green

Treat this as a compatibility assurance task. Run the frozen command/env/data compatibility criteria over all PLAN-002 migrations. If a failure originates in a specific domain/data migration task, reopen that owner rather than adding a second compatibility shim here. Implement here only shared compatibility fixtures/adapters uniquely required by `REQ-NFR-006`.

### Refactor / convergence

Remove temporary duplication introduced by the migration, keep one owner for the policy/capability, and run relevant architecture/contract/conformance checks before considering the task complete.

### Completion evidence

- compatibility/conformance tests
- migration tests
- documentation change log

Also record the quality gates actually run and any environment-gated evidence deferred to PLAN-006.

## TASK-P02-013 — PLAN-002 exit-gate verification

**Primary REQ:** none; plan gate
**Task role:** **plan gate**
**Dependencies:** `TASK-P02-001`, `TASK-P02-002`, `TASK-P02-003`, `TASK-P02-004`, `TASK-P02-005`, `TASK-P02-006`, `TASK-P02-007`, `TASK-P02-008`, `TASK-P02-009`, `TASK-P02-010`, `TASK-P02-011`, `TASK-P02-012`

### Scope

Verify that every primary owner, support/foundation task and assurance task in PLAN-002 satisfies the frozen plan exit gate before work in the next plan is treated as implementation-ready. This task does not add product behavior or reimplement a failed criterion.

### Gate evidence

- Parameterized legal/illegal lifecycle tests pass.
- Legacy DB/snapshot fixtures remain readable.
- Language and duration regressions prove no synthetic English/zero or silent ASR relabeling.
- Job/request context compatibility preserves restart/delivery semantics while the domain model is transport-neutral.
- Canonical write failure cannot lead to successful primary completion.
- Retention classification preserves canonical evidence and artifact-reference truth.
- Frozen operator/data compatibility evidence passes for all changed persisted representations.

### Completion rule

Record commands/evidence, unresolved environment limitations and any failed criterion. A failed criterion MUST be routed to the task that owns the missing behavior or evidence; the gate itself does not patch around the failure. Shared operational evidence may be referenced rather than rerun when it was captured on the same closure revision and remains valid.
