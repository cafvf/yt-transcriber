# F3 — Hexagonal boundaries and provider seams

Status: **In progress — TASK-P03-001..013 locally verified; TASK-P03-014 next**
Plan: `PLAN-003`
Base revision: `f2e265acbcc8b2a4cef601e160ae13193f49d979`
Started: 2026-08-15

## Current increment

### TASK-P03-001 — Bootstrap architecture dependency ratchet

Implemented as the first isolated F3 increment.

Evidence introduced:

- default-discovered architecture test under `tests/conformance/`;
- explicit temporary brownfield manifest at
  `tests/conformance/f3_known_dependency_violations.txt`;
- exact-set comparison: new violations fail and stale manifest entries also fail;
- regression proving a representative `application -> infrastructure` import is detected.

The temporary manifest is migration scaffolding, not an accepted architecture.
Entries must be removed by the task that removes each dependency. `TASK-P03-012`
owns final removal of the manifest and closes `REQ-ARC-001` only when the set is zero.

## Characterized brownfield set

At F3 start the known internal layer violations are confined to:

- `application/pipeline/steps.py` — normalization, snapshot and renderer infrastructure;
- `application/services/rename_speakers.py` — concrete snapshot/renderer infrastructure;
- `application/use_cases/transcribe_video.py` — concrete snapshot infrastructure typing.

No product behavior is changed by this increment.

Local verification:

```text
architecture ratchet: 2 passed
F0/F1/F2/F3 conformance subset: 22 passed
default gate: 759 passed / 47 integration deselected
Ruff + format + diff-check: green
```

### TASK-P03-002 — Provider-secret architectural boundary

Implementation is in progress.

The first seam removes `hf_token` from the application-facing diarization
contract. Authentication becomes constructor-owned by the concrete
infrastructure adapters and is injected at composition.

The backend-internal WhisperX/pyannote calls may still carry the provider token;
that transport is entirely inside infrastructure and is therefore not an
application capability contract.

`AppSettings.hf_token` remains temporarily as compatibility configuration while
TASK-P03-005 establishes the truthful configuration taxonomy. It must not be
reintroduced into application ports or pipeline calls.

Executable evidence is provided by
`tests/conformance/test_provider_secret_boundary.py`.

### TASK-P03-002 local verification

The provider-secret boundary acceptance evidence is locally green:

```text
architecture + provider-secret conformance: 6 passed
diarization/composition regressions: 59 passed
mypy: 105 source files / zero issues
default gate: 763 passed / 47 integration deselected
compileall + Ruff + format + diff-check: green
```

`hf_token` is absent from application port and pipeline source files. Provider
authentication remains internal to concrete diarization infrastructure and is
injected by composition.

Physical separation of credential configuration from ordinary behavioral
configuration remains owned by TASK-P03-005, which must preserve the existing
operator-facing environment names.

### TASK-P03-003 — Port conventions and capability inventory

Implemented; local gate pending.

- explicit current application-port inventory added;
- provider/concrete import rule made executable;
- undeclared new port modules fail the conformance gate;
- `FileStorage` is recorded as the sole temporary generic filesystem exception;
- removal of that exception remains owned by TASK-P03-011;
- no speculative replacement port was created.

Evidence:
- `F3-CAPABILITY-INVENTORY.md`;
- `tests/conformance/f3_application_port_inventory.txt`;
- `tests/conformance/test_application_port_conventions.py`.

### TASK-P03-003 local verification

The port inventory/convention gate is locally green:

```text
architecture/secret/port conformance: 10 passed
P03-001/P03-002 regressions: 59 passed
mypy: 105 source files / zero issues
default gate: 767 passed / 47 integration deselected
compileall + Ruff + format + diff-check: green
```

The source-level provider-secret check is empty for application ports/pipeline.

### TASK-P03-004 — Runtime and hardware policy outside pure domain

Implemented; local gate pending.

- `ModelName` is reduced to opaque model identity;
- filesystem existence checks are removed from the domain;
- VRAM requirements and model-size fallback move to application runtime policy;
- OOM retry consumes the same application-owned smaller-model policy;
- selected runtime model/device/compute facts remain available to processing
  provenance;
- no ASR port redesign is performed here; that remains owned by P03-007.

Executable evidence is provided by
`tests/conformance/test_runtime_policy_boundary.py` plus the existing runtime
selection and pipeline regression suites.

### TASK-P03-004 local verification

The runtime/domain separation gate is locally green:

```text
architecture/runtime conformance: 13 passed
domain model identity: 40 passed
runtime policy: 27 passed
pipeline/OOM/provenance regressions: 32 passed
diarization/composition regressions: 27 passed
mypy: 105 source files / zero issues
default gate: 774 passed / 47 integration deselected
compileall + strict Ruff/format + diff-check: green
```

The domain runtime-policy source scan is empty.

### TASK-P03-005 — Truthful configuration taxonomy and external compatibility

Status: **Locally verified — REQ-ARC-010 closed**

The implementation converges the frozen configuration requirement without
claiming P03-006 ownership prematurely.

#### Acceptance evidence

- **AC-01 — external compatibility:** approved operator-facing environment
  names remain accepted, including `TELEGRAM_BOT_TOKEN`, `HF_TOKEN`,
  `SUMMARY_API_KEY`, `YOUTUBE_COOKIES_FILE`, `YOUTUBE_COOKIES_BROWSER` and
  legacy `MAX_VIDEO_DURATION_MIN`. Flat `AppSettings(...)` constructor
  arguments remain compatible.
- **AC-02 — truthful/source-neutral naming:** generic media processing consumes
  `MediaProcessingSettings.max_media_duration_min`; source-specific YouTube
  and summary settings remain source-specific.
- **AC-03 — credentials separated from behavior policy:** raw provider
  authentication fields are owned by `ProviderCredentials`, not ordinary
  `AppSettings.model_fields` or domain policy objects. `AppSettings` retains
  read-only compatibility properties that delegate to that owner.
- **AC-04 — one fingerprint authority:** `SIGNIFICANT_FIELDS`,
  `processing_fingerprint_payload` and canonical hashing remain owned by
  `application.services.config_signature`; compatibility signature APIs
  delegate to `compute_processing_fingerprint`.

#### Integration boundary

- composition may request credential-owner values when constructing concrete
  providers already migrated by P03-002/P03-005;
- the frozen runtime entrypoint continues to read the flat
  `AppSettings.telegram_bot_token` compatibility property during P03-005;
- explicit end-to-end runtime/composition credential injection and optional
  provider construction remain owned by **TASK-P03-006 / REQ-ARC-011**;
- healthcheck consumes non-secret credential status for token-shape reporting;
- sanitization consumes the exact credential values only for defensive
  redaction/private-path handling;
- this task does not close the remaining external-service disclosure work.

#### Local closure evidence

```text
Ruff auto-fix + format + strict lint: green
mypy: green
REQ-ARC-010 configuration/fingerprint tests: green
security/healthcheck regressions: green
frozen interface/entrypoint/composition regressions: green
F3 conformance set: green
pipeline regression: green
compileall: green
default gate before documentation closure: 783 passed / 47 deselected
git diff --check: green
```

No stage, commit or push is part of this closure.

### TASK-P03-006 — Composition-root ownership of concrete providers and credentials

Status: **Locally verified — REQ-ARC-011 closed**

Implementation boundary:

- `build(..., credentials=...)` receives provider credentials explicitly at the
  composition edge instead of resolving them from ordinary behavior settings;
- YouTube cookies, Hugging Face authentication and the optional summary API key
  are injected only into concrete providers;
- `build_runtime(...)` owns the concrete Telegram provider graph: PTB
  application, bot client, bot adapter, duration inspector and audience/filter;
- `__main__.py` retains handler registration and PTB lifecycle orchestration,
  but no longer selects or constructs project infrastructure adapters;
- runtime summarization selects the tokenizer in composition and injects it into
  `TranscriptSummaryService`;
- `SUMMARY_BACKEND=disabled` exits before optional chat-client/tokenizer
  construction and therefore requires no placeholder summary API credential;
- healthcheck HTTP/models, executable discovery, module discovery, disk usage
  and SQLite probes are explicitly selected by infrastructure/composition;
- persistence, YouTube, conversion, ML, rendering, export and operational
  adapters are wired by the same composition owner.

Scope intentionally deferred:

- backend-neutral ASR request/profile remains P03-007;
- diarization capability/fallback/provenance remains P03-008;
- canonical transcript contracts remain P03-009;
- external-service disclosure minimization remains P03-010.

Local closure evidence:

```text
provider-construction source audit: green
P03-006 composition unit/smoke tests: green
frozen Telegram interface/lifecycle tests: green
F3 architecture/security conformance: green
summarization/tokenizer regressions: green
security/healthcheck regressions: green
diarization regressions: green
local secret scanner: clean
Gitleaks: no leaks found
default gate: 791 passed / 47 deselected / 838 collected
compileall: green
pre-commit security hooks: green
Ruff strict + format check: green
mypy strict: 109 source files / no issues
git diff --check: green
```

No stage, commit or push is part of this local verification.


### TASK-P03-007 — Backend-neutral ASR contract

Status: **Locally verified — REQ-ARC-013 closed**

The application-facing ASR seam now accepts a backend-neutral
`TranscriptionRequest` carrying audio input, language intent, cancellation,
progress and a neutral processing profile. Provider/runtime-shaped
`device`/`compute_type`/`model` arguments no longer define the application port.

WhisperX remains the only concrete ASR backend in this remediation phase. Its
adapter translates the neutral processing target, precision and opaque model id
to WhisperX/CTranslate2-specific arguments internally. No alternative backend,
multilingual expansion or translation feature is introduced by this task.

The pre-task WhisperX behavioral test surface was preserved rather than
replaced: all 19 selected baseline cases remain present and pass against the new
request contract, including language normalization, requested-vs-observed
language truth, OOM/generic error mapping, progress and segment filtering.

#### P03-007 isolated closure evidence

```text
WhisperX behavioral inventory: 19 passed
ASR/runtime/pipeline focused regressions: green
F3 ASR/application-port conformance: green
mypy: 109 source files / zero issues
security scanner + Gitleaks: clean
default gate: 795 passed / 47 deselected / 842 collected
compileall: green
pre-commit security hooks: green
Ruff + format + diff-check: green
```

Integrated on `main` as:

```text
55aaa42 refactor: introduce backend-neutral ASR contract
```

### TASK-P03-010 — External-service disclosure boundary

Status: **Locally verified — REQ-SEC-009 closed**

Outbound text-generation endpoint/model selection is now composition/config
owned. A non-loopback summary endpoint is accepted only when the operator
explicitly configured `SUMMARY_BASE_URL`; loopback defaults remain usable
without fabricated credentials or implicit remote disclosure.

Provider-derived error detail is minimized before crossing operator-visible
error/log boundaries:

- arbitrary OpenAI-compatible HTTP response bodies are omitted rather than
  echoed;
- the established context-window diagnostic is retained only as a canonical
  allowlisted message plus the existing operator hint, not as provider body
  text;
- YouTube/video-export provider detail passes through the shared sanitization
  policy where it is surfaced or logged;
- existing subtitle-fetch semantics remain frozen: non-transient `HTTPError`
  and exhausted transient `URLError` keep their original exception types.

#### P03-010 isolated closure evidence

```text
YouTube/video regression: 56 passed
disclosure/text-generation regression: 55 passed
composition regression: 10 passed
mypy: 110 source files / zero issues
security scanner + Gitleaks: clean
default gate: 807 passed / 47 deselected / 854 collected
compileall: green
pre-commit security hooks: green
Ruff + format + diff-check: green
```

Integrated on `main` as:

```text
df6d116 security: enforce external service disclosure boundary
```

### P03-007 + P03-010 combined integration evidence

The two tasks were implemented and verified in independent Git worktrees, then
integrated as separate commits into the same `main` tree. The combined gate is
the closure evidence that the approved parallel execution did not introduce an
integration conflict.

```text
F3 combined conformance: 34 passed
ASR combined regression: 78 passed
external-service combined regression: 104 passed
default gate: 811 passed / 47 deselected / 858 collected
mypy: 110 source files / zero issues
Ruff: 220 files / green
security scanner: clean
Gitleaks: no leaks
compileall: green
pre-commit security hooks: green
git diff --check: green
combined main worktree: clean
```

No frozen normative plan/task text is changed by this execution closure.


### TASK-P03-008 — Diarization capability, fallback and credential isolation

Status: **Locally verified — REQ-ARC-005 closed**

The application-facing diarization seam now uses a provider-neutral
`DiarizationRequest` carrying the audio input, an application processing target,
speaker-count constraints, progress and cancellation. Provider credentials and
provider API keywords remain confined to concrete infrastructure adapters and
composition.

Fallback semantics are explicit:

- `DiarizationUnavailableError` means the current provider cannot serve the
  request and permits the composite to try the next configured provider;
- hard `DiarizationError` does not silently trigger another provider;
- cancellation propagates as cancellation and is never translated into
  provider failure/fallback;
- zero usable speaker segments, including the case where all raw provider
  segments are rejected by normalization, is treated as explicit provider
  unavailability.

Successful diarization reports observed execution facts through
`DiarizationProvenance`. The pipeline persists the actual winning backend,
explicit model identity and whether fallback was used instead of recording the
composite orchestrator as if it were the concrete backend. The render context
uses the observed diarization model when known, while its existing compatibility
fallback remains in place until TASK-P03-009 owns the renderer/store contract
migration.

Composition explicitly configures the same approved
`pyannote/speaker-diarization-community-1` model identity for the current
WhisperX and direct pyannote adapters. Provider authentication remains
constructor-owned at the infrastructure edge.

#### P03-008 closure evidence

```text
Ruff auto-fix + format + strict lint: green
mypy: 110 source files / zero issues
security scanner: clean
Gitleaks: no leaks
default gate: 823 passed / 47 deselected / 870 collected
diarization contract conformance: 6 passed
diarization adapter/fallback suite: 27 passed
real diarization backend compatibility: 3 passed
snapshot/provenance regression: green
composition/provider-secret/runtime/hexagonal conformance: green
compileall: green
pre-commit security hooks: green
git diff --check: green
```

No frozen normative plan/task text is changed by this execution closure.


### TASK-P03-009 — Canonical transcript store and renderer contracts

Status: **Locally verified — REQ-ARC-006 closed**

Application transcript workflows now depend on explicit, application-owned
capabilities instead of concrete filesystem snapshot and Markdown renderer
classes.

Implementation boundary:

- `application.ports.canonical_transcript` owns the canonical transcript
  record/store contract and the explicit canonical reference used for durable
  save/load;
- `application.ports.transcript_renderer` owns the renderer request/contract;
  rendering consumes structured transcript evidence, aliases and provenance and
  returns Markdown without owning persistence;
- the filesystem snapshot repository implements the canonical store capability
  and preserves version-aware schema decoding;
- missing or corrupt structured evidence is surfaced explicitly rather than
  reconstructed from Markdown filenames or silently ignored;
- `RenderMarkdownStep`, speaker rename and transcription orchestration no longer
  import concrete snapshot/renderer infrastructure;
- transcript text-integrity helpers are application-owned so transcript
  consumers no longer cross the application/infrastructure boundary for
  normalization;
- exporters and summarization consume the canonical structured transcript
  contract while concrete persistence/rendering remain infrastructure adapters;
- composition injects the concrete canonical store and renderer implementations.

The migration ratchet now reports zero known forbidden
`application -> infrastructure` imports. The temporary
`f3_known_dependency_violations.txt` manifest is intentionally retained as empty
scaffolding because final removal remains owned by TASK-P03-012.

#### P03-009 closure evidence

```text
canonical transcript contract conformance: 17 passed
default gate: 840 passed / 47 deselected / 887 collected
integration gate: 47 passed / 840 deselected / 887 collected
mypy: 113 source files / zero issues
Ruff auto-fix + format + strict lint: 225 files / green
security scanner: clean
Gitleaks: 41 commits / ~2.99 MB scanned / no leaks
compileall: green
pre-commit security hooks: green
git diff --check: green
known dependency violation set: zero
```

Integrated locally on `main` as:

```text
0d5d154 refactor: establish canonical transcript store and renderer contracts
```

No frozen normative plan/task text is changed by this execution closure.


### TASK-P03-011 — Remove obsolete generic FileStorage surface

Status: **Locally verified — support/convergence for REQ-ARC-012**

Repository/reference characterization found no approved runtime consumer of the
generic `FileStorage` capability. The remaining executable surface consisted
only of the application port itself, its `LocalFileStorage` adapter, composition
construction/exposure, the temporary port-inventory exception and 11 integration
tests dedicated to that obsolete abstraction.

P03-009 had already established the purpose-specific canonical transcript store
and renderer contracts. Existing job/history persistence capabilities remain
purpose-specific. No demonstrated storage need therefore required preservation
of a generic filesystem port.

Implementation boundary:

- deleted `application/ports/file_storage.py`;
- deleted the concrete `LocalFileStorage` filesystem adapter;
- removed `LocalFileStorage` construction and `Composition.file_storage`
  exposure from the composition root;
- deleted the 11 integration tests that protected only the retired generic
  abstraction;
- removed `file_storage.py` from the executable application-port inventory;
- replaced the temporary exception conformance rule with a post-P03-011 guard
  that forbids generic storage modules and the retired `FileStorage` /
  `LocalFileStorage` runtime symbols;
- introduced no renamed generic storage abstraction.

This task satisfies the generic-storage cleanup precondition for
`REQ-ARC-012`; it does **not** close that requirement. Final capability-port
closure remains owned by TASK-P03-013 after TASK-P03-012 closes the dependency
direction invariant.

#### P03-011 closure evidence

```text
focused architecture/canonical/composition gate: 36 passed
default gate: 840 passed / 36 deselected / 876 collected
integration gate: 36 passed / 840 deselected / 876 collected
mypy: 111 source files / zero issues
Ruff auto-fix + format + strict lint: 213 files / green
security scanner: clean
Gitleaks: 43 commits / ~3.02 MB scanned / no leaks
compileall: green
pre-commit security hooks: green
runtime FileStorage/LocalFileStorage scan: empty
known application -> infrastructure violation set: zero
git diff --check: green
```

Integrated locally on `main` as:

```text
c666305 refactor: remove obsolete generic file storage surface
```

No frozen normative plan/task text is changed by this execution closure.


### TASK-P03-012 — Mechanically enforced dependency direction

Status: **Locally verified — REQ-ARC-001 closed**

The temporary PLAN-003 dependency ratchet has converged into a permanent
zero-violation architecture invariant.

Implementation boundary:

- removed `tests/conformance/f3_known_dependency_violations.txt`; no legacy
  exception manifest remains;
- `test_hexagonal_dependencies.py` now requires the forbidden dependency set to
  be empty directly;
- domain runtime code is mechanically prevented from importing application or
  infrastructure modules;
- application runtime code is mechanically prevented from importing concrete
  infrastructure modules;
- the architecture checks remain part of the default pytest gate;
- representative regression coverage proves a newly introduced
  `application -> infrastructure` import is detected;
- direct application stdlib I/O is scanned separately from layer imports so it
  cannot become a loophole around the dependency rule;
- current direct-I/O hotspots are mechanically matched to their frozen
  purpose-specific requirement/task owners; new ungoverned hotspots fail and
  stale routing entries also fail.

The direct-I/O governance metadata is not a dependency-exception allowlist.
P03-012 changes no production behavior. Remaining purpose-specific I/O
migrations stay with their frozen owners, including P03-013 for application
capability closure and PLAN-004 operational-policy/I/O separation.

#### P03-012 closure evidence

```text
conformance gate: 74 passed
default gate: 842 passed / 36 deselected / 878 collected
integration gate: 36 passed / 842 deselected / 878 collected
mypy: 111 source files / zero issues
Ruff auto-fix + format + strict lint: 213 files / green
security scanner: clean
Gitleaks: 45 commits / ~3.03 MB scanned / no leaks
compileall: green
pre-commit security hooks: green
forbidden domain/application import scans: empty
legacy dependency manifest: absent
git diff --check: green
```

Integrated locally on `main` as:

```text
561e691 test: enforce dependency direction without legacy exceptions
```

`REQ-ARC-001` is closed. No frozen normative plan/task text is changed by this
execution closure.


### TASK-P03-013 — Purpose-specific application-owned ports

Status: **Locally verified — REQ-ARC-012 closed**

The PLAN-003 application-port boundary has converged on narrow,
application-owned capability contracts with executable cross-cutting
conformance.

Implementation boundary:

- removed the unused transport-specific `split_for_telegram()` operation from
  the generic `AudioConverter` application port;
- removed the corresponding dead FFmpeg segmentation/ffprobe implementation,
  fake method and tests that protected only that unused surface;
- retained the approved audio-conversion capability and current runtime
  behavior;
- added executable conformance that rejects transport/provider-specific
  operation names in application ports;
- added executable proof that every abstract application-port contract in the
  explicit inventory can be implemented by a plain test double without
  importing infrastructure;
- retained the P03-011 guards that forbid generic storage modules and the
  retired `FileStorage` / `LocalFileStorage` runtime symbols;
- retained the P03-012 zero-violation dependency invariant;
- introduced no speculative replacement capability and no new product
  behavior.

Source-specific concepts remain source-specific where they are part of an
approved capability. `IncomingMedia.file_id` remains the opaque Telegram media
reference used by the approved private-media flow, and YouTube subtitle track
metadata remains inside the approved YouTube-specific acquisition capability.
No provider credential or SDK object crosses an application port.

#### P03-013 closure evidence

```text
focused gate: 57 passed / 2 deselected
default gate: 840 passed / 35 deselected / 875 collected
integration gate: 35 passed / 840 deselected / 875 collected
final port conformance: 49 passed
mypy: 111 source files / zero issues
Ruff auto-fix + format + strict lint: 213 files / green
security scanner: clean
Gitleaks: 47 commits / ~3.04 MB scanned / no leaks
compileall: green
pre-commit security hooks: green
split_for_telegram runtime/test scan: empty
generic FileStorage/runtime storage scan: empty
forbidden application -> infrastructure import scan: empty
git diff --check: green
```

Integrated locally on `main` as:

```text
04bc56c refactor: close purpose-specific port conformance
```

`REQ-ARC-012` is closed. No frozen normative plan/task text is changed by this
execution closure.


## Next task

Proceed to `TASK-P03-014 — PLAN-003 exit-gate verification`.

## Gate state

F3 remains **open**. TASK-P03-014 must verify the frozen PLAN-003 exit gate on
the integrated closure revision. It is a verification task and must route any
failed criterion back to its owning task rather than patching behavior itself.
