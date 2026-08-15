# UC-004 — Browse and retrieve completed history

Version: **1.0.1**
Status: **Approved / Frozen**
Derived from: **000-baseline v1.0.0**
Reference date: **2026-08-15**

## Goal

Browse completed transcript history and retrieve a saved canonical human-readable transcript.

## Primary actor

Authorized Operator

## Trigger

`/list` or `/last [n]`.

## Preconditions

- The operator is authorized.
- History persistence is available.

## Main success scenario

1. Completed Jobs are selected in deterministic operator-scoped order.
2. `/list` presents recent entries with deterministic positional indexes over the current completed-history ordering.
3. These indexes are not durable identifiers: they may shift when completed history changes.
4. `/last [n]` resolves the selected completed Job from the current ordering and delivers its saved Markdown.


## Alternative and exception flows

- Empty history and invalid/out-of-range indexes are explicit.
- Missing Markdown is reported; transcription is not re-run implicitly.

## Postconditions

- History inspection does not mutate transcript content or reprocess media.

## Security and privacy notes

- Titles, source identity, timestamps, and transcript files are private.

## Current evidence references

- `docs/01-contrato-funcional.md`
- `docs/03-manual-de-uso.md`
- `src/yt_transcriber_bot/infrastructure/telegram/history.py`

## Requirement dimensions to derive

- deterministic ordering/selection
- Markdown availability
- privacy scoping
- error behavior
