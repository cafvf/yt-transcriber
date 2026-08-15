# UC-001 — Transcribe or explicitly reprocess media

Version: **1.0.0**
Status: **Approved / Frozen**
Derived from: **000-baseline v1.0.0**
Reference date: **2026-08-15**

## Goal

Obtain a durable, auditable transcript from a supported YouTube source or private Telegram audio, including an explicit request to process a YouTube source again as a new Job, while preserving source identity, provenance, lifecycle, failure, and delivery semantics.

## Primary actor

Authorized Operator

## Trigger

The operator submits a YouTube URL directly or through `/transcribe`, `/pt`, `/en`, or `/redo`; or submits supported Telegram audio/voice/audio-document media.

## Preconditions

- The request originates from the configured authorized Telegram user.
- Required runtime configuration for the selected path is available.
- Queue capacity is available before acceptance.
- Source-specific type, size, duration, and language constraints are satisfied.

## Main success scenario

1. The system identifies the source without inventing YouTube identity for Telegram media.
2. The system validates source-specific constraints and creates a new durable Job with sufficient request/provenance data.
3. The Job enters the sequential processing queue.
4. For YouTube, metadata is obtained and an eligible subtitle track may replace ASR.
5. When audio processing is required, the system acquires/uses the media, converts it, selects runtime policy, transcribes, and diarizes.
6. The system produces canonical structured transcript evidence and canonical Markdown rendering.
7. The Job enters delivery and applicable artifacts are sent through Telegram.
8. After successful delivery the Job becomes `completed` and is available to history and derivative workflows.

## Alternative and exception flows

- Unauthorized users are silently ignored.
- Invalid/unsupported input, excessive limits, unsupported language, unavailable source, or full queue is rejected explicitly.
- Equivalent active/pending work may be deduplicated according to current policy.
- Unsuitable YouTube subtitles fall back to audio/ASR.
- Processing failures end in `failed`; cooperative cancellation ends in `cancelled`; exhausted delivery retry ends in `delivery_failed` with local artifacts preserved.
- **Explicit reprocessing (`/redo`)** creates a distinct new Job and re-enters this same flow. It does not reopen or mutate a terminal historical Job. Current baseline does not require confirmation, configuration diff, or selective stage reuse.

## Postconditions

- Successful processing yields durable completed Job state and canonical transcript evidence.
- Failed/cancelled/delivery-failed work has an explicit terminal outcome.
- Explicit reprocessing preserves previous Jobs and artifacts as historical records.

## Security and privacy notes

- Provider credentials are not Job business payload.
- Telegram media, transcripts, snapshots, logs, identifiers, and derivatives are private.
- Diagnostics are sanitized. Reprocessing/provenance must never expose credentials.

## Current evidence references

- `docs/01-contrato-funcional.md`
- `docs/03-manual-de-uso.md`
- `src/yt_transcriber_bot/application/use_cases/transcribe_video.py`
- `src/yt_transcriber_bot/application/pipeline/steps.py`
- `src/yt_transcriber_bot/infrastructure/telegram/bot_adapter.py`

## Requirement dimensions to derive

- source/input behavior and validation
- media identity taxonomy
- Job lifecycle/state machine
- queue/dedup/resource limits
- processing and delivery semantics
- canonical transcript/provenance
- explicit new-Job reprocessing
- security/sanitization
- compatibility for legacy persisted state
