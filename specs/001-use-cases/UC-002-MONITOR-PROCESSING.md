# UC-002 — Monitor processing and queue

Version: **1.0.0**
Status: **Approved / Frozen**
Derived from: **000-baseline v1.0.0**
Reference date: **2026-08-15**

## Goal

Understand active processing and pending work without mutating it or exposing unnecessary private content.

## Primary actor

Authorized Operator

## Trigger

`/status`, `/queue`, or `/fila`.

## Preconditions

- The operator is authorized.

## Main success scenario

1. The system obtains a consistent view of active Job and pending queue.
2. Relevant state/position information is presented.
3. Output is minimized to operational metadata needed by the operator.

## Alternative and exception flows

- Idle/empty state is reported explicitly.
- Unavailable underlying state yields a sanitized operational error.

## Postconditions

- Inspection does not change Job lifecycle or queue ordering.

## Security and privacy notes

- Queue/job metadata are private; secrets and transcript bodies are omitted.

## Current evidence references

- `docs/03-manual-de-uso.md`
- `src/yt_transcriber_bot/infrastructure/telegram/job_queue.py`
- `src/yt_transcriber_bot/infrastructure/telegram/bot_adapter.py`

## Requirement dimensions to derive

- status projection
- queue consistency
- observability
- privacy/minimization
