# GATE-P07-A — Truthful Canonical Semantics

Version: **1.0.0**
Status: **Approved for implementation derivation**
Gate model: **GATES.md v1.0.0**
Baseline audited: **6f77d24f2c82d4748fd777056325f629c6fdf27a**

## 1. Purpose

Gate A establishes a single truthful vocabulary for the existing product before error-boundary,
packaging or documentation convergence begins.

It is a semantic/domain/application convergence gate. It SHALL NOT redesign providers, add
translation, add new product features, or create abstractions with no demonstrated current contract.

The gate owns `TASK-P07-001` through `TASK-P07-005`.

## 2. Brownfield observations that motivate the gate

At the audited baseline:

- `DownloadedAudio.used_alternate_track` is documented as `True` when alternate/auto-dub tracks exist
  **and the original track was selected**.
- `PipelineContext.audio_track_was_dubbed` receives that value, inverting the apparent meaning again.
- `MediaMetadata` already exists, but internal code still imports the compatibility name
  `VideoMetadata`.
- `PipelineContext` carries requested/effective/observed language and language source as strings even
  though `Language` and `LanguageSource` already exist.
- `compute_processing_fingerprint` is already the canonical fingerprint authority, while compatibility
  names still exist and `Job` still exposes `config_signature`.
- generic application code is already guarded against `max_video_duration_min`, but the external
  compatibility name may still exist.
- `ArtifactClass` already classifies canonical, derived and volatile artifacts, while `Job` still has
  a free-form `artifact_policy` string whose real behavioral ownership must be established before it
  is typed or removed.

These are treated as brownfield evidence, not as requirements to preserve.

## 3. Canonical decisions

### DEC-A-001 — Selected audio semantics

Introduce a canonical typed selection fact named `AudioTrackSelection`.

Minimum values:

- `ORIGINAL` — provider evidence identifies the downloaded format as the original track;
- `DEFAULT` — the ordinary/default audio path was selected and there is no evidence that a distinct
  original-vs-dub choice was necessary;
- `UNKNOWN` — a download succeeded but available provider evidence cannot truthfully classify it.

`AUTO_DUB` is **not** a successful selection state under the current product policy. When provider
evidence identifies a candidate as auto-dubbed, it SHALL NOT be silently accepted as the chosen
audio in place of an identifiable original.

`MediaMetadata.has_alternate_audio_tracks` remains a separate fact. Existence of alternate tracks does
not imply that an alternate track was selected.

Canonical result shape:

```text
DownloadedAudio
├─ audio_path
├─ container
├─ track_selection: AudioTrackSelection
└─ metadata: MediaMetadata
```

`used_alternate_track` and `audio_track_was_dubbed` are not canonical and have no presumed
compatibility entitlement.

### DEC-A-002 — MediaMetadata ownership

`MediaMetadata` is the internal domain/application type.

Internal imports of `VideoMetadata` SHALL be migrated. A `VideoMetadata` alias/module shim may remain
only if a concrete supported external/persisted dependency is found and registered as `COMPAT-*`.

Tests and internal source references do not by themselves justify compatibility; they are migrated
with the canonical code.

The preferred module name is `media_metadata.py`. If renaming the module reveals a real import
compatibility requirement, retain a minimal deprecated shim only at that module boundary.

### DEC-A-003 — Typed PipelineContext language state

Canonical application state:

```text
requested_language: Language | None
transcription_language: Language | None
observed_language: Language | None
language_source: LanguageSource
```

`LanguageSource.UNKNOWN` is the default rather than `None`/free-form `"unknown"`.

Strings may exist at:

- Telegram/user command parsing;
- environment/config parsing;
- provider payload parsing;
- persistence compatibility;
- renderer/serialization output.

They SHALL be converted once at the boundary and remain typed inside the application flow.

Regional provider codes such as `en-US` are normalized by the provider adapter before constructing
the two-letter `Language` value object.

Do not introduce a new subtitle-kind enum merely because `youtube_subtitle_kind` is currently a
string. First audit whether it carries information not already represented by `LanguageSource` and
`youtube_subtitle_used`. If fully derivable, remove the duplicate state.

### DEC-A-004 — Processing fingerprint

`processing_fingerprint` is the sole canonical application/domain concept for result-significant
processing configuration.

Compatibility names such as `config_signature`, `transcription_signature()` and
`compute_config_signature()` follow this decision tree:

```text
usage audit
  ├─ only current internal callers/tests → migrate callers and remove legacy name
  └─ supported persisted/external caller → boundary compatibility + COMPAT record + test
```

Physical database column names MAY remain legacy if repository mapping isolates them and a standalone
rename migration would add risk without behavioral benefit.

### DEC-A-005 — Duration and artifact policy

`max_media_duration_min` remains canonical inside application code.

`MAX_VIDEO_DURATION_MIN` may remain only as an external config alias covered by COMPAT-004 and
precedence tests.

For `Job.artifact_policy`:

1. audit all writers/readers/branches;
2. if it is a constant with no meaningful variant, remove it rather than creating an enum;
3. if multiple real policies affect behavior, model that policy explicitly using existing
   `ArtifactClass` values or a small value object whose semantics are defined by those classes;
4. preserve a legacy physical persistence representation only when required for existing data.

No new free-form artifact-policy strings may be introduced.

## 4. Invariants after Gate A

The following SHALL hold simultaneously:

- source-neutral domain/application code uses `MediaMetadata`;
- YouTube-specific concepts remain isolated to YouTube behavior;
- selected audio and existence of alternates are independent facts;
- known auto-dub is never silently presented as original/default;
- unknown audio/language facts remain unknown;
- language state is typed after boundary parsing;
- one canonical fingerprint concept exists;
- generic duration policy uses media terminology;
- artifact policy has one truthful owner or is removed if not real;
- every retained legacy name has a `COMPAT-*` justification;
- all inherited frozen architecture/data/security tests still pass.

## 5. Gate A implementation order

Within Gate A the implementation order is:

```text
A1 characterize current intended behavior
 ↓
TASK-P07-001 audio-track semantics
 ↓
TASK-P07-002 MediaMetadata migration
 ↓
TASK-P07-003 typed language flow
 ↓
TASK-P07-004 processing fingerprint migration
 ↓
TASK-P07-005 duration/artifact-policy convergence
 ↓
A2 taxonomy/compatibility conformance
 ↓
A3 cumulative Gate A quality gate
```

Small commits are preferred, but no TASK receives independent release approval. Gate A is the unit of
architectural acceptance.

## 6. Gate A non-goals

- stable cross-provider error-code system (Gate B);
- Markdown filesystem boundary refactor (Gate B);
- production env-file redesign (Gate C);
- dependency-group/package build redesign (Gate C);
- README rewrite (Gate D);
- release artifact/full operational proof (Gate E).

A Gate A change that makes one of these areas unavoidable must preserve behavior and record the handoff
rather than silently implementing a later gate.
