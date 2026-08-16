# F3 — Hexagonal boundaries and provider seams

Status: **In progress — TASK-P03-001..005 locally verified; TASK-P03-006 next**
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

## Next task

After the P03-005 local gate is green, proceed to
`TASK-P03-006 — Composition-root ownership of concrete providers and credentials`.

## Gate state

F3 remains **open**. PLAN-003 exit verification belongs to `TASK-P03-014` after all
preceding tasks close.
