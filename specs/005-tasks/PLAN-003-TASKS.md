# PLAN-003 Tasks — Hexagonal boundaries and provider seams

Version: **1.0.0**
Status: **Approved / Frozen**
Derived from: **004-planning v1.0.0 (Approved / Frozen)**

## Execution rule

Tasks follow Red → Green → Refactor where executable behavior can be reproduced. Foundation tasks may establish a ratchet/seam before the corresponding cross-cutting REQ is closed; the designated **closure owner** verifies the full frozen REQ after dependent migrations. Host-only evidence follows preflight/rehearsal semantics rather than fabricated unit Red tests. No task may create a parallel policy or generic abstraction merely to satisfy sequencing.

## TASK-P03-001 — Bootstrap architecture dependency ratchet

**Primary REQ:** none; supports frozen requirements without closing them
**Supports:** `REQ-ARC-001`
**Task role:** **support / foundation**
**Dependencies:** `TASK-P02-013`

### Scope

Introduce the executable architecture check required by `REQ-ARC-001` in a ratcheting mode: record the known brownfield dependency violations explicitly, fail on any new violation, and make the check part of the default quality gate. This task establishes the migration guardrail; it does **not** claim `REQ-ARC-001` is closed while known violations remain.

**Integration note:** Downstream PLAN-003 tasks depend on this guardrail being active, not on full closure of `REQ-ARC-001`.

### Red / characterization

Characterize the current domain/application dependency violations and prove that the new check detects at least one representative forbidden dependency without blocking the planned cleanup behind an undocumented exception.

### Green

Add the architecture test plus an explicit temporary violation manifest scoped only to known baseline deviations. New violations fail immediately. The manifest is removed by `TASK-P03-012`, the `REQ-ARC-001` closure task.

### Refactor / convergence

Do not create a second source of policy truth. Remove temporary migration scaffolding when the owning closure task has replacement evidence.

### Completion evidence

- architecture test executes in the default gate;
- known-violation manifest is explicit and reviewable;
- a regression proves new violations fail.
## TASK-P03-002 — Provider-secret architectural boundary

**Primary REQ:** `REQ-SEC-008`
**Task role:** **change owner**
**Dependencies:** `TASK-P02-013`

### Implementation intent

Provider-specific credentials SHALL be resolved and consumed at composition/infrastructure boundaries and SHALL not become domain entity fields, application business payloads or generic application-port parameters.

**Current brownfield focus:** The diarization port transports `hf_token`, and application `AppSettings` currently owns raw provider secrets.

**Likely touchpoints:** Diarization/text-generation/provider credentials in ports, payloads, settings consumers and composition.

### Red

Create or strengthen the lowest useful tests that express the frozen acceptance boundary:

- AC-01: No provider token/cookie/API-key field exists in domain entities.
- AC-02: Generic application ports do not accept provider credentials such as `hf_token`.
- AC-03: Application requests carry business/security-neutral capability inputs rather than provider authentication material.
- AC-04: Concrete adapters receive their authentication configuration from composition/edge configuration.

If all acceptance criteria are already satisfied, record characterization evidence instead of manufacturing an artificial failing test. For host-only or environment-only criteria, a failing preflight/rehearsal criterion is valid Red evidence; do not fabricate a unit-test substitute.

### Green

Implement the minimum coherent change required to satisfy the failing acceptance evidence while preserving all upstream frozen behavior and the current plan ownership boundary.

### Refactor / convergence

Remove temporary duplication introduced by the migration, keep one owner for each policy/capability, and run relevant architecture/contract/conformance checks before considering the task complete.

### Completion evidence

- architecture/conformance scan for credential-shaped domain/application parameters
- port contract tests
- composition-root tests

Also record the quality gates actually run and any environment-gated evidence deferred to PLAN-006.
## TASK-P03-003 — Establish purpose-specific port conventions and capability inventory

**Primary REQ:** none; supports frozen requirements without closing them
**Supports:** `REQ-ARC-012`
**Task role:** **support / foundation**
**Dependencies:** `TASK-P02-013`, `TASK-P03-001`, `TASK-P03-002`

### Scope

Establish the application-owned port conventions needed to implement `REQ-ARC-012`: inventory each current external capability, define where narrow application-facing contracts live, and add structural tests that forbid provider credentials, provider API shapes and generic filesystem escape hatches. This task is a foundation; specific ASR, diarization and canonical-transcript contracts are implemented by their dedicated tasks.

**Integration note:** `REQ-ARC-012` remains open until TASK-P03-013 verifies all capability contracts; TASK-P03-011 removes the obsolete generic FileStorage surface and TASK-P03-012 closes the prerequisite architecture-direction invariant.

### Red / characterization

Inventory current application-to-external interactions and characterize provider-shaped/generic contracts that must be replaced. Add a structural test that can distinguish an application capability contract from a provider/generic-I/O surface.

### Green

Create only the minimal port organization/conventions and shared conformance checks required by current approved capabilities. Do not pre-create speculative ports and do not remove `FileStorage` until replacement/no-consumer evidence exists.

### Refactor / convergence

Do not create a second source of policy truth. Remove temporary migration scaffolding when the owning closure task has replacement evidence.

### Completion evidence

- capability inventory mapped to approved requirements;
- port-location/conformance rules executable;
- no speculative generic replacement abstraction.
## TASK-P03-004 — Runtime and hardware policy outside pure domain

**Primary REQ:** `REQ-ARC-004`
**Task role:** **change owner**
**Dependencies:** `TASK-P02-013`, `TASK-P03-001`

### Implementation intent

Hardware detection and runtime/model/compute selection policy SHALL remain outside pure domain objects and SHALL be expressed as application/runtime policy whose selected facts can be recorded in run provenance.

**Current brownfield focus:** `ModelName` and related runtime concepts currently mix domain identity with filesystem/VRAM/provider policy.

**Likely touchpoints:** `ModelName`, runtime selection, GPU detector and model/runtime facts recorded as application/runtime policy.

### Red

Create or strengthen the lowest useful tests that express the frozen acceptance boundary:

- AC-01: Domain value objects do not query filesystem, CUDA, VRAM or installed-model state.
- AC-02: Application/runtime policy can select an execution profile from configuration plus detected hardware capability.
- AC-03: Concrete ML adapters translate the selected application/runtime profile into provider-specific device/compute/model options.
- AC-04: Known selected runtime/model facts are available to run provenance.

If all acceptance criteria are already satisfied, record characterization evidence instead of manufacturing an artificial failing test. For host-only or environment-only criteria, a failing preflight/rehearsal criterion is valid Red evidence; do not fabricate a unit-test substitute.

### Green

Implement the minimum coherent change required to satisfy the failing acceptance evidence while preserving all upstream frozen behavior and the current plan ownership boundary.

### Refactor / convergence

Remove temporary duplication introduced by the migration, keep one owner for each policy/capability, and run relevant architecture/contract/conformance checks before considering the task complete.

### Completion evidence

- domain-purity architecture tests
- runtime-selection unit tests
- provenance tests

Also record the quality gates actually run and any environment-gated evidence deferred to PLAN-006.
## TASK-P03-005 — Truthful configuration taxonomy and external compatibility

**Primary REQ:** `REQ-ARC-010`
**Task role:** **change owner**
**Dependencies:** `TASK-P02-013`, `TASK-P03-001`, `TASK-P03-002`

### Implementation intent

Internal configuration SHALL have a single truthful concern owner for each setting, keep credential configuration separated from ordinary behavior policy, and preserve approved operator-facing environment-variable compatibility while allowing source-neutral internal naming.

**Current brownfield focus:** Configuration is monolithic and fingerprint/signature logic currently has overlapping authorities.

**Likely touchpoints:** Internal settings grouping, compatibility aliases, processing fingerprint inputs and configuration-loading ownership.

### Red

Create or strengthen the lowest useful tests that express the frozen acceptance boundary:

- AC-01: Existing approved operator environment-variable names remain accepted or have an explicit versioned migration.
- AC-02: Generic media/application settings use source-neutral internal names; source-specific names remain only for source-specific behavior.
- AC-03: Domain policy objects can be constructed without provider credential values.
- AC-04: Processing-fingerprint field selection has one canonical authority and does not diverge across duplicate configuration-signature implementations.

If all acceptance criteria are already satisfied, record characterization evidence instead of manufacturing an artificial failing test. For host-only or environment-only criteria, a failing preflight/rehearsal criterion is valid Red evidence; do not fabricate a unit-test substitute.

### Green

Implement the minimum coherent change required to satisfy the failing acceptance evidence while preserving all upstream frozen behavior and the current plan ownership boundary.

### Refactor / convergence

Remove temporary duplication introduced by the migration, keep one owner for each policy/capability, and run relevant architecture/contract/conformance checks before considering the task complete.

### Completion evidence

- configuration compatibility tests
- fingerprint conformance tests
- secret-boundary architecture tests

Also record the quality gates actually run and any environment-gated evidence deferred to PLAN-006.
## TASK-P03-006 — Composition-root ownership of concrete providers and credentials

**Primary REQ:** `REQ-ARC-011`
**Task role:** **change owner**
**Dependencies:** `TASK-P02-013`, `TASK-P03-002`, `TASK-P03-003`, `TASK-P03-005`

### Implementation intent

Composition/runtime SHALL select and configure concrete Telegram, YouTube, persistence, ML, tokenizer/text-generation and operational adapters, injecting only application-facing capabilities inward and retaining provider credentials at the edge.

**Current brownfield focus:** No specific brownfield defect is singled out; preserve approved behavior while establishing the required contract.

**Likely touchpoints:** Composition root/provider construction, trusted endpoints, credential injection and current adapter selection.

### Red

Create or strengthen the lowest useful tests that express the frozen acceptance boundary:

- AC-01: Runtime wiring has one clear composition owner.
- AC-02: Provider tokens, cookies and API keys are resolved at the edge and are not forwarded through generic domain/application requests.
- AC-03: Optional capabilities can be disabled without fake credentials.
- AC-04: Composition smoke tests verify the configured object graph without external network calls where practical.

If all acceptance criteria are already satisfied, record characterization evidence instead of manufacturing an artificial failing test. For host-only or environment-only criteria, a failing preflight/rehearsal criterion is valid Red evidence; do not fabricate a unit-test substitute.

### Green

Implement the minimum coherent change required to satisfy the failing acceptance evidence while preserving all upstream frozen behavior and the current plan ownership boundary.

### Refactor / convergence

Remove temporary duplication introduced by the migration, keep one owner for each policy/capability, and run relevant architecture/contract/conformance checks before considering the task complete.

### Completion evidence

- composition-root tests
- architecture credential scan

Also record the quality gates actually run and any environment-gated evidence deferred to PLAN-006.
## TASK-P03-007 — Backend-neutral ASR contract

**Primary REQ:** `REQ-ARC-013`
**Task role:** **change owner**
**Dependencies:** `TASK-P02-013`, `TASK-P03-003`, `TASK-P03-004`

### Implementation intent

The application ASR contract SHALL express backend-independent transcription inputs, constraints, progress/cancellation and structured results rather than WhisperX/CTranslate2-specific device, compute-type or model-library parameters.

**Current brownfield focus:** Current application ASR contract exposes Whisper/CTranslate2-shaped device, compute type and model parameters.

**Likely touchpoints:** Application transcription request/result contract plus WhisperX adapter translation and contract tests.

### Red

Create or strengthen the lowest useful tests that express the frozen acceptance boundary:

- AC-01: Generic ASR request carries transcribable audio, requested/forced language constraint when present, cancellation/progress and an application processing profile as needed.
- AC-02: ASR result can represent independently observed language/confidence separately from a forced/user-requested language constraint.
- AC-03: Concrete adapter translates the application processing profile into backend-specific device/compute/model arguments.
- AC-04: Unsupported independent language observations are surfaced truthfully and are never silently relabeled to an allowed language.

If all acceptance criteria are already satisfied, record characterization evidence instead of manufacturing an artificial failing test. For host-only or environment-only criteria, a failing preflight/rehearsal criterion is valid Red evidence; do not fabricate a unit-test substitute.

### Green

Implement the minimum coherent change required to satisfy the failing acceptance evidence while preserving all upstream frozen behavior and the current plan ownership boundary.

### Refactor / convergence

Remove temporary duplication introduced by the migration, keep one owner for each policy/capability, and run relevant architecture/contract/conformance checks before considering the task complete.

### Completion evidence

- shared ASR contract tests
- WhisperX adapter tests
- language/provenance regression tests

Also record the quality gates actually run and any environment-gated evidence deferred to PLAN-006.
## TASK-P03-008 — Diarization capability, fallback and credential isolation

**Primary REQ:** `REQ-ARC-005`
**Task role:** **change owner**
**Dependencies:** `TASK-P02-013`, `TASK-P03-002`, `TASK-P03-003`, `TASK-P03-004`

### Implementation intent

Application diarization SHALL use a provider-neutral capability contract with explicit fallback/error semantics and provenance, while provider authentication is configured inside concrete adapters/composition rather than passed through the application port.

**Current brownfield focus:** Current diarization application port carries `hf_token` and provider-shaped runtime inputs.

**Likely touchpoints:** Application diarization capability, composite fallback semantics, provider adapters, credential injection and provenance.

### Red

Create or strengthen the lowest useful tests that express the frozen acceptance boundary:

- AC-01: The application diarization port has no provider credential parameter such as `hf_token`.
- AC-02: Primary/fallback adapters implement common speaker-segment result/error semantics.
- AC-03: Fallback conditions are explicit and tested.
- AC-04: Known actual diarization backend/model/fallback facts are available for run provenance.

If all acceptance criteria are already satisfied, record characterization evidence instead of manufacturing an artificial failing test. For host-only or environment-only criteria, a failing preflight/rehearsal criterion is valid Red evidence; do not fabricate a unit-test substitute.

### Green

Implement the minimum coherent change required to satisfy the failing acceptance evidence while preserving all upstream frozen behavior and the current plan ownership boundary.

### Refactor / convergence

Remove temporary duplication introduced by the migration, keep one owner for each policy/capability, and run relevant architecture/contract/conformance checks before considering the task complete.

### Completion evidence

- shared diarization contract tests
- fallback regression tests
- architecture credential scan

Also record the quality gates actually run and any environment-gated evidence deferred to PLAN-006.
## TASK-P03-009 — Canonical transcript store and renderer contracts

**Primary REQ:** `REQ-ARC-006`
**Task role:** **change owner**
**Dependencies:** `TASK-P02-013`, `TASK-P03-003`

### Implementation intent

Application transcript-consuming workflows SHALL depend on explicit canonical transcript store and rendering capabilities rather than concrete filesystem snapshot/Markdown renderer classes or filename conventions.

**Current brownfield focus:** Application services/pipeline currently type or import concrete snapshot/renderer infrastructure classes.

**Likely touchpoints:** Canonical transcript store/render contracts, current snapshot/Markdown adapters, rename/export/summary consumers.

### Red

Create or strengthen the lowest useful tests that express the frozen acceptance boundary:

- AC-01: Canonical transcript store supports durable save/load by explicit canonical transcript reference and version-aware decoding.
- AC-02: Renderer consumes structured transcript evidence plus aliases/provenance and returns Markdown content without owning storage.
- AC-03: Rename, summary, export and history workflows do not import the concrete filesystem snapshot repository.
- AC-04: Missing/corrupt structured evidence is surfaced explicitly to the application workflow.

If all acceptance criteria are already satisfied, record characterization evidence instead of manufacturing an artificial failing test. For host-only or environment-only criteria, a failing preflight/rehearsal criterion is valid Red evidence; do not fabricate a unit-test substitute.

### Green

Implement the minimum coherent change required to satisfy the failing acceptance evidence while preserving all upstream frozen behavior and the current plan ownership boundary.

### Refactor / convergence

Remove temporary duplication introduced by the migration, keep one owner for each policy/capability, and run relevant architecture/contract/conformance checks before considering the task complete.

### Completion evidence

- port contract tests
- architecture import tests
- workflow tests with fake/in-memory store

Also record the quality gates actually run and any environment-gated evidence deferred to PLAN-006.
## TASK-P03-010 — External-service disclosure boundary

**Primary REQ:** `REQ-SEC-009`
**Task role:** **change owner**
**Dependencies:** `TASK-P02-013`, `TASK-P03-002`, `TASK-P03-006`

### Implementation intent

Data SHALL cross an external-service boundary only as required for the explicitly configured approved operation, with endpoint/provider choice controlled by trusted configuration and with private payloads minimized to that operation.

**Current brownfield focus:** No specific brownfield defect is singled out; preserve approved behavior while establishing the required contract.

**Likely touchpoints:** Text-generation/YouTube/provider outbound adapters, endpoint allow/config policy and payload minimization.

**Integration note:** Reuse PLAN-001 sanitization/privacy policy; do not introduce a second disclosure filter.

### Red

Create or strengthen the lowest useful tests that express the frozen acceptance boundary:

- AC-01: Transcript text is sent to a non-local text-generation endpoint only when such an endpoint was explicitly configured by the operator.
- AC-02: External-service requests do not include unrelated credentials, local paths, logs or private payload classes that the provider does not need.
- AC-03: Provider endpoint/model identity used for an operation comes from trusted configuration rather than transcript/provider response content.
- AC-04: External errors and response bodies are sanitized before persistence or display.

If all acceptance criteria are already satisfied, record characterization evidence instead of manufacturing an artificial failing test. For host-only or environment-only criteria, a failing preflight/rehearsal criterion is valid Red evidence; do not fabricate a unit-test substitute.

### Green

Implement the minimum coherent change required to satisfy the failing acceptance evidence while preserving all upstream frozen behavior and the current plan ownership boundary.

### Refactor / convergence

Remove temporary duplication introduced by the migration, keep one owner for each policy/capability, and run relevant architecture/contract/conformance checks before considering the task complete.

### Completion evidence

- external-boundary contract tests
- text-generation boundary tests
- security review for configured external endpoints

Also record the quality gates actually run and any environment-gated evidence deferred to PLAN-006.
## TASK-P03-011 — Remove obsolete generic FileStorage surface after replacement/no-consumer evidence

**Primary REQ:** none; supports frozen requirements without closing them
**Supports:** `REQ-ARC-012`
**Task role:** **support / convergence**
**Dependencies:** `TASK-P02-013`, `TASK-P03-003`, `TASK-P03-006`, `TASK-P03-009`

### Scope

Remove only the obsolete generic `FileStorage` port/adapter/composition exposure once repository/reference evidence proves no approved runtime consumer needs it and purpose-specific capabilities cover the demonstrated needs. Cleanup of unrelated empty/speculative packages belongs to `REQ-NFR-005` in PLAN-004 and is deliberately excluded here.

**Integration note:** This task satisfies the cleanup precondition of `REQ-ARC-012`; it does not own the broader PLAN-004 speculative-abstraction cleanup.

### Red / characterization

Use architecture/reference tests or repository search assertions to prove `FileStorage` is unused by approved consumers and that any demonstrated storage need has purpose-specific replacement coverage.

### Green

Delete the unused generic port, concrete adapter/wiring and tests that only protect the obsolete generic surface. Do not delete unrelated domain packages or introduce a renamed generic storage abstraction.

### Refactor / convergence

Do not create a second source of policy truth. Remove temporary migration scaffolding when the owning closure task has replacement evidence.

### Completion evidence

- no approved consumer imports/constructs generic FileStorage;
- replacement capability tests remain green;
- composition smoke remains green.
## TASK-P03-012 — Mechanically enforced dependency direction

**Primary REQ:** `REQ-ARC-001`
**Task role:** **closure owner**
**Dependencies:** `TASK-P02-013`, `TASK-P03-001`, `TASK-P03-002`, `TASK-P03-003`, `TASK-P03-004`, `TASK-P03-005`, `TASK-P03-006`, `TASK-P03-007`, `TASK-P03-008`, `TASK-P03-009`, `TASK-P03-010`, `TASK-P03-011`

### Implementation intent

The approved layer dependency direction SHALL be mechanically enforced so domain remains independent of application/infrastructure and application remains independent of concrete infrastructure.

**Current brownfield focus:** No specific brownfield defect is singled out; preserve approved behavior while establishing the required contract.

**Likely touchpoints:** Default architecture test, removal of the temporary known-violation manifest and final domain/application import/I/O-boundary scan.

### Red

Create or strengthen the lowest useful tests that express the frozen acceptance boundary:

- AC-01: Domain runtime code imports only approved stdlib/domain dependencies.
- AC-02: Application runtime code does not import infrastructure modules.
- AC-03: Architecture checks execute in the default quality gate.
- AC-04: Direct stdlib access to external I/O from application is governed by purpose-specific boundary requirements rather than used as a loophole around the dependency rule.

If all acceptance criteria are already satisfied, record characterization evidence instead of manufacturing an artificial failing test. For host-only or environment-only criteria, a failing preflight/rehearsal criterion is valid Red evidence; do not fabricate a unit-test substitute.

### Green

Remove the temporary architecture-violation manifest only after the preceding seam migrations eliminate every known forbidden import. Do not patch functional behavior in this closure task; route any remaining violation to its owning migration task. The task closes only when the default architecture gate passes with no legacy exception list.

### Refactor / convergence

Remove temporary duplication introduced by the migration, keep one owner for each policy/capability, and run relevant architecture/contract/conformance checks before considering the task complete.

### Completion evidence

- architecture dependency tests in the default gate

Also record the quality gates actually run and any environment-gated evidence deferred to PLAN-006.
## TASK-P03-013 — Purpose-specific application-owned ports

**Primary REQ:** `REQ-ARC-012`
**Task role:** **closure owner**
**Dependencies:** `TASK-P02-013`, `TASK-P03-002`, `TASK-P03-003`, `TASK-P03-006`, `TASK-P03-007`, `TASK-P03-008`, `TASK-P03-009`, `TASK-P03-011`, `TASK-P03-012`

### Implementation intent

External capabilities required by application behavior SHALL cross narrow application-owned ports or equivalent application abstractions that express the capability needed rather than a provider API or generic filesystem surface.

**Current brownfield focus:** No specific brownfield defect is singled out; preserve approved behavior while establishing the required contract.

**Likely touchpoints:** Application port inventory/conformance, test doubles, provider-neutral signatures and the absence of generic FileStorage.

### Red

Create or strengthen the lowest useful tests that express the frozen acceptance boundary:

- AC-01: Ports are owned in application-facing modules and can be implemented by test doubles without importing infrastructure.
- AC-02: Port parameters/results use application/domain concepts and exclude provider credentials or unrelated transport payloads.
- AC-03: A generic filesystem abstraction is not retained solely to avoid defining the actual capability required by a workflow.
- AC-04: Unused generic `FileStorage` is removed once all current consumers/capabilities have explicit replacement coverage.

If all acceptance criteria are already satisfied, record characterization evidence instead of manufacturing an artificial failing test. For host-only or environment-only criteria, a failing preflight/rehearsal criterion is valid Red evidence; do not fabricate a unit-test substitute.

### Green

Treat this as a closure task after `REQ-ARC-001` is closed. Run every frozen acceptance criterion across the ports created by the preceding PLAN-003 tasks. If a failure belongs to a specific ASR, diarization, transcript-store, composition or cleanup task, reopen that task rather than duplicating its implementation here. Implement here only residual cross-cutting port-conformance mechanics uniquely owned by `REQ-ARC-012`.

### Refactor / convergence

Remove temporary duplication introduced by the migration, keep one owner for each policy/capability, and run relevant architecture/contract/conformance checks before considering the task complete.

### Completion evidence

- port architecture/conformance tests
- capability-level contract tests

Also record the quality gates actually run and any environment-gated evidence deferred to PLAN-006.
## TASK-P03-014 — PLAN-003 exit-gate verification

**Primary REQ:** none; plan gate
**Task role:** **plan gate**
**Dependencies:** `TASK-P03-001`, `TASK-P03-002`, `TASK-P03-003`, `TASK-P03-004`, `TASK-P03-005`, `TASK-P03-006`, `TASK-P03-007`, `TASK-P03-008`, `TASK-P03-009`, `TASK-P03-010`, `TASK-P03-011`, `TASK-P03-012`, `TASK-P03-013`

### Scope

Verify that every primary owner, support/foundation task and assurance task in PLAN-003 satisfies the frozen plan exit gate before work in the next plan is treated as implementation-ready. This task does not add product behavior or reimplement a failed criterion.

### Gate evidence

- Domain/application dependency rules pass in the default gate with no legacy exception list.
- Application ports carry no provider credentials.
- Trusted external endpoints/provider selection remain composition/config owned.
- ASR and diarization shared contract tests pass against current adapters.
- Canonical transcript consumers run with fake/in-memory capabilities.
- Composition smoke tests validate the graph without requiring real network calls.
- No generic replacement abstraction exists without an approved demonstrated capability.

### Completion rule

Record commands/evidence, unresolved environment limitations and any failed criterion. A failed criterion MUST be routed to the task that owns the missing behavior or evidence; the gate itself does not patch around the failure. Shared operational evidence may be referenced rather than rerun when it was captured on the same closure revision and remains valid.
