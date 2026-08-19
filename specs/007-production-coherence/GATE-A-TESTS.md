# GATE-P07-A — Test Catalogue

Version: **1.0.0**
Status: **Approved for TDD implementation**

## 1. Test policy

Tests derive from `GATE-A-SPEC.md` and `GATE-A-USE-CASES.md`.

Prefer extending an existing test owner when appropriate. Create a new test module only when no
current module expresses the contract cleanly. Do not move tests cosmetically.

Each reproducible semantic defect first receives a Red regression test unless the existing test
already demonstrates the defect and can be corrected to the newly approved expectation.

## 2. TASK-P07-001 tests — audio-track selection

| ID | Scenario | Level | Expected |
|---|---|---|---|
| TC-A001 | ordinary single audio path | adapter unit | selection DEFAULT; no alternates |
| TC-A002 | single track explicitly marked original | adapter unit | ORIGINAL |
| TC-A003 | original + auto-dub | adapter unit | original candidate downloaded; ORIGINAL |
| TC-A004 | regional original code `en-US` | adapter unit | original language `en` |
| TC-A005 | alternate regional/duplicate languages | adapter unit | normalized/deduplicated alternates |
| TC-A006 | non-DRC + DRC original candidates | adapter unit | deterministic non-DRC preference |
| TC-A007 | first original candidate fails, second succeeds | adapter unit | second original attempted; no dub |
| TC-A008 | all original candidates fail | adapter unit | YouTube failure; no generic auto-dub fallback |
| TC-A009 | alternates known but original cannot be identified safely | adapter unit | no false ORIGINAL; policy-safe failure/unknown path |
| TC-A010 | output path/file absent after provider success payload | adapter unit | acquisition failure |
| TC-A011 | pipeline consumes typed selection | application unit | no `audio_track_was_dubbed` mutation |
| TC-A012 | selection independent of `has_alternate_audio_tracks` | domain/contract | orthogonal facts |
| TC-A013 | legacy misleading field absent from canonical DTO/context | conformance | no internal use |
| TC-A014 | no-audio behavior preserved | regression | existing failure semantics |

Primary existing owner to extend:
`tests/unit/infrastructure/youtube/test_youtube_runtime_compatibility.py`.

The current assertion that original selection implies `used_alternate_track is True` SHALL become Red
evidence for the approved semantic correction rather than be preserved.

## 3. TASK-P07-002 tests — MediaMetadata

| ID | Scenario | Level | Expected |
|---|---|---|---|
| TC-A015 | YouTube metadata requires video_id | domain unit | invalid object rejected |
| TC-A016 | Telegram/source-neutral metadata without video_id | domain unit | valid when source facts support it |
| TC-A017 | unknown duration/language stay None | conformance | truthful unknown |
| TC-A018 | source_reference wins canonical reference | domain unit | exact source reference |
| TC-A019 | YouTube video_id fallback canonical URL | domain unit | canonical YouTube URL |
| TC-A020 | no canonical reference evidence | domain unit | explicit error |
| TC-A021 | no internal `VideoMetadata` symbol/import | conformance AST/text | zero violations |
| TC-A022 | no `video_metadata.py` compatibility shim unless registered | conformance | absence or matching COMPAT record |
| TC-A023 | legacy persisted snapshots remain readable without VideoMetadata alias | integration/compat | persisted data unaffected |

Existing owners:
- `tests/conformance/test_domain_data_truth.py`
- existing media metadata/domain tests if present.

## 4. TASK-P07-003 tests — typed language flow

| ID | Scenario | Level | Expected |
|---|---|---|---|
| TC-A024 | PipelineContext field annotations | conformance | Language/LanguageSource types |
| TC-A025 | requested language accepted | application unit | requested/effective typed; REQUESTED |
| TC-A026 | requested vs metadata disagreement | application unit | requested wins; diagnostic only |
| TC-A027 | requested outside allowlist | regression | LanguageNotAllowedError |
| TC-A028 | metadata language accepted | application unit | typed effective; METADATA |
| TC-A029 | metadata outside allowlist | regression | LanguageNotAllowedError |
| TC-A030 | no request/no metadata | application unit | None + UNKNOWN, no default |
| TC-A031 | ASR detected language | application unit | typed result |
| TC-A032 | ASR observed language absent | application unit | remains None |
| TC-A033 | ASR observed language present | application unit | distinct typed observed fact |
| TC-A034 | manual YouTube subtitles | application unit | YOUTUBE_MANUAL |
| TC-A035 | auto YouTube subtitles | application unit | YOUTUBE_AUTO |
| TC-A036 | requested language preserved through subtitle path | application unit | separate requested fact |
| TC-A037 | regional provider language normalized at adapter | adapter unit | two-letter Language |
| TC-A038 | invalid raw code rejected before core state | boundary/unit | ValueError/config validation |
| TC-A039 | no `.value`/string roundtrip required inside pipeline core | conformance | no targeted violations |
| TC-A040 | subtitle-kind duplicate removed or independently specified | conformance | no redundant mutable truth |

Gate A SHALL preserve the existing anti-fabrication assertions such as no `allowed[0]`, no implicit
`"pt"` fallback and unknown transcript language/source behavior.

## 5. TASK-P07-004 tests — processing fingerprint

| ID | Scenario | Level | Expected |
|---|---|---|---|
| TC-A041 | credential/path/bookkeeping differences | conformance/unit | same fingerprint |
| TC-A042 | requested language difference | unit | different fingerprint |
| TC-A043 | source type difference | unit | different fingerprint |
| TC-A044 | one significant-field authority | conformance AST | one owner |
| TC-A045 | Job/application canonical field vocabulary | conformance | processing_fingerprint |
| TC-A046 | legacy DB column mapping if retained | persistence integration | roundtrip canonical value |
| TC-A047 | legacy serialized field if retained | compatibility fixture | translated once |
| TC-A048 | compatibility delegates retained only with COMPAT entry | conformance | registry matches code |
| TC-A049 | fingerprint payload contains no credentials/private paths | security/conformance | forbidden fields absent |

Existing owner:
`tests/conformance/test_configuration_taxonomy.py` plus persistence tests.

## 6. TASK-P07-005 tests — duration/artifact policy

| ID | Scenario | Level | Expected |
|---|---|---|---|
| TC-A050 | generic application duration naming | conformance | no max_video_duration_min use outside boundary |
| TC-A051 | legacy env alias alone | config unit | canonical media value |
| TC-A052 | canonical + legacy env supplied | config unit | documented deterministic precedence |
| TC-A053 | duration limit behavior unchanged | application regression | same acceptance/rejection semantics |
| TC-A054 | artifact_policy usage inventory | conformance | every usage classified |
| TC-A055 | no free-form new artifact policy strings | conformance | no unowned variants |
| TC-A056 | real policy variants, if any | domain/application unit | typed behavior grounded in ArtifactClass |
| TC-A057 | no real policy variant | domain/conformance | canonical field removed |
| TC-A058 | legacy persisted policy value, if needed | persistence compat | old Job loads without defining new core semantics |

## 7. Cross-cutting Gate A tests

| ID | Scenario | Expected |
|---|---|---|
| TC-A059 | retained COMPAT entries have executable evidence | registry and tests agree |
| TC-A060 | legacy names do not spread into new core code | taxonomy scan clean |
| TC-A061 | Telegram media does not fabricate YouTube identity | source-neutral conformance |
| TC-A062 | unknown facts remain unknown | data-truth conformance |
| TC-A063 | domain→application/infrastructure violations | none |
| TC-A064 | application→infrastructure violations | none |
| TC-A065 | provider credentials in domain/application contracts | none |
| TC-A066 | existing default regression suite | green |
| TC-A067 | security scanners | execute successfully and green |
| TC-A068 | secret-like fixtures/examples introduced by Gate A | none |
| TC-A069 | docs/spec vocabulary matches implemented canonical names | conformance/manual review |
| TC-A070 | exact Gate A completion SHA recorded | evidence record |

## 8. Expected test ownership

Do not create one giant `test_gate_a.py`.

Likely ownership:

```text
tests/unit/domain/
    media metadata / language / new audio selection VO as applicable

tests/unit/application/pipeline/
    requested/effective/observed language and DownloadAudioStep behavior

tests/unit/infrastructure/youtube/
    original/alternate format detection and download selection

tests/conformance/
    PLAN-007 taxonomy
    compatibility registry
    configuration taxonomy
    domain data truth
    hexagonal dependencies

tests/integration/
    persistence compatibility only where a retained legacy representation requires it
```

## 9. Red → Green → Refactor sequence

### Red 1 — audio semantic contradiction
Change/add tests so selecting the original track no longer expects a misleading `True` boolean.

### Green 1
Introduce typed selection and migrate the pipeline.

### Red/Green 2 — MediaMetadata
Add conformance that forbids internal `VideoMetadata`; migrate imports/module.

### Red/Green 3 — typed languages
Assert typed context and behavior; eliminate string roundtrips from core flow.

### Red/Green 4 — fingerprint
Assert canonical Job/application naming; migrate callers and map retained persistence names.

### Red/Green 5 — duration/artifact
Audit first, then test the chosen removal/typing outcome. Do not pre-create an abstraction.

### Refactor
Remove compatibility scaffolding that has no evidence; minimize duplicate state; run the cumulative
Gate A suite.

## 10. No test theater

Forbidden:

- asserting private helper names solely to lock implementation;
- testing enum member count without behavioral reason;
- mocks that reproduce yt-dlp internals more deeply than needed to express provider payloads;
- preserving a wrong legacy assertion because it already exists;
- adding `# type: ignore`, skip markers or allowlists merely to make the gate green;
- weakening existing domain truth tests.
