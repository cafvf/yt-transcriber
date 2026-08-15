# UC-008 — Export a transcript

Version: **1.0.0**
Status: **Approved / Frozen**
Derived from: **000-baseline v1.0.0**
Reference date: **2026-08-15**

## Goal

Generate a supported text/structured/subtitle representation from canonical transcript evidence without re-running transcription.

## Primary actor

Authorized Operator

## Trigger

`/text`, `/export`, `/json`, `/srt`, or `/vtt`.

## Preconditions

- The operator is authorized.
- Completed transcript evidence exists.
- Requested format is supported.

## Main success scenario

1. The completed transcript is selected.
2. Structured evidence and aliases/provenance are loaded as required.
3. Requested supported format is rendered.
4. The artifact is delivered.

## Alternative and exception flows

- Unsupported formats or invalid indexes are rejected.
- Missing canonical snapshot is reported rather than rebuilt from media/Markdown.

## Postconditions

- Canonical evidence is unchanged and export reflects current aliases.

## Security and privacy notes

- Export content is private; names/metadata must not leak credentials or unnecessary paths.

## Current evidence references

- `src/yt_transcriber_bot/infrastructure/exporting/plain_text_exporter.py`
- `src/yt_transcriber_bot/infrastructure/exporting/transcript_exporter.py`

## Requirement dimensions to derive

- format contracts
- canonical transcript dependency
- timestamp/speaker representation
- private artifact handling
