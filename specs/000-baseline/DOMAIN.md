# Baseline Domain Specification

Version: **1.0.0**
Status: **Approved**
Baseline date: **2026-08-15**

## 1. Purpose

This document defines the domain language before detailed use cases and atomic requirements.

The code evolved from YouTube-only transcription into a system that also processes private Telegram audio. Some historical names no longer describe the full domain accurately.

## 2. Core concepts

### Media Source

Identifies the origin of media without embedding transport payloads or provider credentials.

Current source types include YouTube media and private Telegram audio.

Source identity and source acquisition are separate concepts.

### Media

Input content used for transcription processing.

### Job

Durable identity and lifecycle record of one processing request.

A Job records sufficient metadata for ownership/authorization context, source identity, requested processing choices, lifecycle status, artifact references, and failure/recovery semantics.

### Transcript

Canonical logical representation of recognized spoken content, including segments, timestamps, language information, and speaker labels where available.

When persisted, the versioned structured transcript snapshot is the canonical machine-readable representation. Markdown is the canonical human-readable rendering of that structured evidence, not the machine source from which structure should be reconstructed.

### Speaker label / rename

A diarization backend may produce anonymous labels. A rename associates a user-facing name without changing source evidence.

### Artifact

Persisted output associated with a Job. Artifacts may be canonical or derived.

## 3. Source identity versus transport

Telegram can be the interaction transport and, for uploads, also the source mechanism.

A Telegram command containing a YouTube URL uses Telegram as transport while YouTube remains the media source.

A Telegram audio upload should avoid retaining unnecessary transport payloads in domain identity.

## 4. Job lifecycle

The baseline distinguishes semantic state names from compatibility serialization.

Semantic status vocabulary:

- `pending`
- `acquiring`
- `converting`
- `transcribing`
- `diarizing`
- `rendering`
- `delivering`
- `completed`
- `delivery_failed`
- `failed`
- `cancelled`

`acquiring` means that the job is resolving/preparing its media source for the common pipeline. The current persisted string `"downloading"` is a historical compatibility representation of this state and may remain serialized during the baseline to avoid destructive database migration. Internal code should converge on source-neutral terminology while compatibility readers/writers continue to understand historical data.

### 4.1 Semantic transition graph

The candidate baseline semantics are:

```text
pending
  -> acquiring
  -> cancelled
  -> failed

acquiring
  -> converting          # common ASR path
  -> rendering           # accepted YouTube-subtitle shortcut
  -> cancelled
  -> failed

converting
  -> transcribing
  -> cancelled
  -> failed

transcribing
  -> diarizing
  -> cancelled
  -> failed

diarizing
  -> rendering
  -> cancelled
  -> failed

rendering
  -> delivering
  -> failed

delivering
  -> completed
  -> delivery_failed
```

Restart reconciliation additionally applies the same terminal outcomes:

- legacy/incomplete `pending` work that cannot be reconstructed becomes `failed`;
- interrupted `acquiring`/legacy `downloading`, `converting`, `transcribing`, `diarizing`, or `rendering` work becomes `failed`;
- interrupted `delivering` work becomes `delivery_failed`;
- valid `pending` work may be re-enqueued while remaining `pending`.

Repeated assignment of the same status, such as implementation-level `acquiring -> acquiring` (currently serialized as `downloading -> downloading`), is not a domain transition and must not be required by the future state-machine implementation.

### 4.2 Cancellation semantics

Cancellation is cooperative. The domain allows cancellation from pre-delivery processing states where the application observes a cancellation request. It does not promise interruption of an already-running external call at arbitrary instruction boundaries.

The baseline does not define cancellation of `delivering`; once delivery semantics begin, the outcome is completion or delivery failure.

## 5. Terminal-state semantics

`completed`, `delivery_failed`, `failed`, and `cancelled` are terminal in the baseline domain.

`delivery_failed` remains terminal for this baseline. A future explicit resend/re-delivery capability must be modeled as a separate approved use case and must not silently reopen the original processing lifecycle.

## 6. Taxonomy corrections to evaluate

Candidates include:

- `TranscribeVideoUseCase`;
- `VideoMetadata`;
- `max_video_duration_min`;
- `VideoTooLongError`;
- `JobPayload.url`;
- persisted `video_id` usage outside genuine YouTube identity.

Renaming must preserve compatibility where persistent schemas, env vars, commands, exported metadata, or documentation depend on historical names.

## 7. Domain purity

A domain value object validates intrinsic properties, not external state such as filesystem existence.

Hardware requirements and backend compatibility are runtime/backend policy unless there is a clear domain reason to encode them centrally.

## 8. Configuration provenance

A Job records a processing fingerprint representing configuration categories that may materially affect transcript output or its canonical evidence.

The fingerprint is a single, versioned concept. Its semantic input includes, where applicable:

- source/acquisition policy that can change transcript source selection, such as subtitle preference;
- audio-preparation parameters that can materially affect ASR input;
- ASR backend/model selection and result-significant inference parameters;
- language constraints/hints that materially affect recognition;
- diarization backend/model and result-significant diarization parameters;
- transcript normalization/schema policy when a policy-version change can alter canonical text/segments.

Operational-only settings are excluded, including credentials, filesystem paths, Telegram/chat identifiers, queue sizes, retention limits, log verbosity, progress intervals, and other values that do not define transcript content.

Actual runtime/provenance metadata may record additional facts such as device or fallback path even when those facts are not part of fingerprint identity.

Current overlapping configuration-signature mechanisms must converge on one canonical owner before advanced reprocessing/backend expansion.

## 9. Non-goals

This baseline does not yet define detailed use cases, atomic requirements, translation artifacts, semantic-search entities, multi-user tenancy, cross-job speaker identity, or checkpoint/resume aggregates.
