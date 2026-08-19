# GATE-P07-A — Use Cases, Alternatives and Error Cases

Version: **1.0.0**
Status: **Approved for test derivation**

Use-case IDs are architectural behavior scenarios. They are not tied to private helper methods.

# TASK-P07-001 — Audio-track selection semantics

## UC-A001 — Single ordinary audio track

**Given** a YouTube item exposes one usable ordinary/default audio path and no evidence of alternate
audio tracks
**When** audio is acquired
**Then** acquisition succeeds, `has_alternate_audio_tracks=False`, and selection is `DEFAULT` unless
provider evidence explicitly proves `ORIGINAL`.

### Alternatives
- A001-A: provider labels the only track explicitly as original → `ORIGINAL`.
- A001-B: provider metadata lacks original-language information → language remains unknown; selection
  is not inferred from language absence.

### Error/edge
- A001-E1: no usable audio stream → existing no-audio failure semantics preserved.
- A001-E2: output file not created → acquisition fails; no false successful DTO is returned.

## UC-A002 — Original plus auto-dub alternatives

**Given** provider format metadata identifies one or more original candidates and one or more
auto-dubbed alternatives
**When** acquisition runs
**Then** an original candidate is explicitly selected, metadata records alternate availability and
languages, and selection is `ORIGINAL`.

### Alternatives
- A002-A: original language uses a regional code (`en-US`) → normalized to `Language("en")`.
- A002-B: original marker appears in `format_note`.
- A002-C: original marker appears in another supported provider field/name.
- A002-D: DRC and non-DRC original candidates exist → deterministic preference preserves the current
  non-DRC-first intent.

### Error/edge
- A002-E1: first original candidate fails but another original candidate succeeds → retry only among
  eligible original candidates.
- A002-E2: all identifiable original candidates fail → fail acquisition; do not silently select an
  auto-dub.
- A002-E3: alternate tracks are known but no original candidate can be identified safely → fail
  closed or return only a policy-approved truthful unknown path; never claim original.
- A002-E4: duplicate/regional alternate language entries → normalize and deduplicate.

## UC-A003 — Selected-track fact is independent from alternate availability

**Given** alternate tracks exist
**Then** `has_alternate_audio_tracks=True` does not imply an alternate track was used.

**Given** no alternate tracks exist
**Then** selection still truthfully reports `DEFAULT`, `ORIGINAL` or `UNKNOWN` based on provider
evidence rather than forcing a boolean interpretation.

## UC-A004 — Pipeline consumes canonical track selection

**When** `DownloadAudioStep` receives `DownloadedAudio`
**Then** it stores/uses the typed selected-track fact without translating it into
`audio_track_was_dubbed`.

### Error/edge
- A004-E1: any legacy field found to be externally required must be translated at one boundary and
  registered as compatibility; otherwise it is removed.

# TASK-P07-002 — MediaMetadata convergence

## UC-A005 — YouTube metadata

A YouTube metadata object requires a YouTube `video_id`; known fields remain typed and unknown fields
remain `None`.

## UC-A006 — Telegram/uploaded media metadata

Source-neutral media metadata can represent Telegram/uploaded audio without fabricating a YouTube
`video_id`, provided the source identity/reference rules are satisfied.

## UC-A007 — Canonical reference resolution

- source reference present → canonical reference comes from it;
- no source reference but YouTube `video_id` present → canonical YouTube URL;
- neither exists when a canonical URL is requested → explicit error, not fabricated data.

## UC-A008 — Internal canonical import

Domain/application consumers import/use `MediaMetadata`. `VideoMetadata` is absent internally unless
a registered compatibility shim is proven necessary.

### Error/edge
- A008-E1: module rename breaks a real supported external import → add a minimal shim + COMPAT entry;
  do not restore old terminology throughout the core.
- A008-E2: only tests/current source use old import → migrate them; this is not backward compatibility.

# TASK-P07-003 — Typed language flow

## UC-A009 — Explicit requested language

**Given** user input has already been validated/parsed at the boundary into `Language`
**When** processing begins
**Then** requested language is typed, allowlist validation uses the typed value, and effective
transcription language is the requested language with `LanguageSource.REQUESTED`.

### Alternative
- A009-A: metadata disagrees with user request → user request remains authoritative and diagnostic
  records the disagreement without mutating either fact.

### Error
- A009-E1: requested language outside allowlist → existing `LanguageNotAllowedError` behavior remains.
- A009-E2: malformed raw language code → rejected at boundary/value-object construction, not stored as
  an arbitrary application string.

## UC-A010 — Metadata language with no explicit request

Known metadata language becomes the typed effective language source `METADATA` for subtitle/model
selection while preserving the existing policy that ASR may still observe/detect language.

### Error
- A010-E1: metadata language outside allowlist → existing policy rejection preserved.

## UC-A011 — Unknown language before ASR

If request and metadata language are both absent, typed state remains:

- requested: `None`;
- effective/transcription language: `None` until actual evidence exists;
- language source: `UNKNOWN`.

No default `pt`, `en`, first allowlisted language or other fabricated fact is inserted.

## UC-A012 — ASR returns language evidence

ASR output is converted once into typed `Language` and `LanguageSource`. Observed language and
confidence remain distinct from requested/effective language.

### Alternatives
- A012-A: ASR supplies detected language but no observed language → missing fact remains `None`.
- A012-B: ASR supplies confidence only for supported language fact → confidence attaches to that fact;
  unrelated confidence is not fabricated.

## UC-A013 — YouTube manual subtitle path

Eligible manual subtitle selection sets typed language state and
`LanguageSource.YOUTUBE_MANUAL`; requested language remains separately preserved.

## UC-A014 — YouTube automatic subtitle path

Eligible accepted auto subtitle selection sets `LanguageSource.YOUTUBE_AUTO`; it is not confused with
ASR or metadata language provenance.

## UC-A015 — Duplicate subtitle-kind state audit

If `youtube_subtitle_kind` is fully derivable from `youtube_subtitle_used` + `LanguageSource`, remove
the duplicate mutable string. If not derivable, document its independent contract before typing it.

# TASK-P07-004 — Processing fingerprint convergence

## UC-A016 — Same significant processing choices

Two settings instances differing only in credentials, paths or operational bookkeeping produce the
same processing fingerprint.

## UC-A017 — Different result-significant choices

Changing a result-significant field, requested language or source type changes the fingerprint where
the current canonical policy says it is significant.

## UC-A018 — New Job/application state uses canonical fingerprint terminology

New application/domain code receives/stores/references `processing_fingerprint`, not
`config_signature`.

### Alternatives
- A018-A: physical DB column remains `config_signature` → repository mapper translates it.
- A018-B: old serialized representation has legacy field → compatibility reader translates it.

### Error/edge
- A018-E1: usage audit finds only internal callers of `compute_config_signature` or
  `transcription_signature()` → migrate/remove rather than register compatibility.
- A018-E2: supported external caller is proven → compatibility delegate stays with deprecation record.

## UC-A019 — Fingerprint privacy

Credentials, secret values and non-result-significant private paths remain excluded from the
fingerprint payload.

# TASK-P07-005 — Duration and artifact-policy convergence

## UC-A020 — Canonical media duration setting

Application processing code consumes `max_media_duration_min`. Existing duration rejection behavior
does not change merely because terminology changes.

## UC-A021 — Legacy external duration variable

If `MAX_VIDEO_DURATION_MIN` remains supported, config parsing translates it into canonical media
settings deterministically and records it as COMPAT-004.

### Error/edge
- A021-E1: canonical and legacy env names both supplied → precedence is explicit and tested; ambiguity
  is not silently accepted.

## UC-A022 — Artifact policy has real behavioral meaning

Audit finds multiple artifact-policy variants that actually change product behavior → represent the
policy with a typed domain/application concept grounded in `ArtifactClass`.

## UC-A023 — Artifact policy is not a real variable concept

Audit finds `artifact_policy` is effectively a fixed/default string with no meaningful branching →
remove it from canonical domain/application state rather than inventing a new enum.

### Compatibility
- A023-A: persisted legacy column/value is needed to load old jobs → persistence mapper/reader handles
  it without reintroducing a free-form domain field unless the behavior still exists.

# Cross-task Gate A use cases

## UC-A024 — Legacy compatibility is boundary-local

Every retained legacy surface maps exactly once to canonical state and never appears as a required
input to new core logic.

## UC-A025 — Unknown remains unknown

Across media metadata, selected audio classification, language and provenance, lack of evidence never
becomes a convenient default.

## UC-A026 — Source neutrality

Telegram/uploaded audio can pass through shared media/application concepts without acquiring fake
YouTube/video semantics.

## UC-A027 — Frozen behavior outside Gate A remains unchanged

Search, transcription, diarization, rendering, delivery, cancellation, persistence and existing
operator behavior not explicitly changed by Gate A remain protected by regression tests.
