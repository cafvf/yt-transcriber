# UC-012 — Clear reconstructible cache/model data

Version: **1.0.0**
Status: **Approved / Frozen**
Derived from: **000-baseline v1.0.0**
Reference date: **2026-08-15**

## Goal

Remove only configured reconstructible cache/model data without deleting durable Job/history/transcript evidence.

## Primary actor

Authorized Operator

## Trigger

`/clearcache`.

## Preconditions

- The operator is authorized.
- Approved cache/model target is known.

## Main success scenario

1. The approved reconstructible cache scope is resolved.
2. Eligible content is removed.
3. A sanitized result is returned.

## Alternative and exception flows

- Missing cache is a no-op/empty condition.
- Filesystem errors are sanitized.
- Deletion never escapes the intended cache boundary.

## Postconditions

- Canonical Job/history/transcript artifacts remain intact; later ML work may need to rebuild/download cache.

## Security and privacy notes

- Path containment is mandatory; cache must not be a credential store.

## Current evidence references

- `src/yt_transcriber_bot/infrastructure/telegram/bot_adapter.py`

## Requirement dimensions to derive

- safe deletion scope
- path containment
- reconstructibility
- operator feedback
