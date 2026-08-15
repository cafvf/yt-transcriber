# UC-006 — Rename or merge speaker labels

Version: **1.0.0**
Status: **Approved / Frozen**
Derived from: **000-baseline v1.0.0**
Reference date: **2026-08-15**

## Goal

Replace anonymous diarization labels with operator-selected names and re-render the human-readable transcript without re-running ASR/diarization.

## Primary actor

Authorized Operator

## Trigger

`/rename [n]` plus rename interaction.

## Preconditions

- The operator is authorized.
- Completed structured transcript evidence exists.
- Target labels exist.

## Main success scenario

1. Canonical structured transcript evidence is loaded.
2. Existing labels are presented/selected.
3. Non-empty aliases are supplied for valid labels.
4. Effective aliases are persisted with the Job.
5. Markdown is re-rendered from structured evidence and aliases.
6. Affected search/index state is refreshed according to current behavior.

## Alternative and exception flows

- Unknown labels/blank aliases do not corrupt the transcript.
- Missing snapshot fails explicitly; Markdown is not parsed as a substitute canonical store.

## Postconditions

- Segment identity remains unchanged; aliases and Markdown are durable.

## Security and privacy notes

- Speaker names may be personally identifying data and remain private.

## Current evidence references

- `src/yt_transcriber_bot/application/services/rename_speakers.py`
- `src/yt_transcriber_bot/infrastructure/persistence/filesystem/transcript_snapshot.py`

## Requirement dimensions to derive

- transcript-store contract
- alias validation/persistence
- re-rendering
- search refresh
- privacy
