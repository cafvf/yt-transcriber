# UC-003 — Cancel active or pending work

Version: **1.0.0**
Status: **Approved / Frozen**
Derived from: **000-baseline v1.0.0**
Reference date: **2026-08-15**

## Goal

Cancel the active Job, pending Jobs, or both within current cooperative-cancellation semantics.

## Primary actor

Authorized Operator

## Trigger

`/cancel`, `/clearqueue`/aliases, or `/cancelall`/alias.

## Preconditions

- The operator is authorized.

## Main success scenario

1. The system resolves the requested cancellation scope.
2. Targeted pending Jobs are removed from the queue and persisted `cancelled`.
3. Active work receives a cooperative cancellation signal.
4. Disposable Telegram staging for cancelled pending work is cleaned when applicable.
5. The operator receives a truthful result.

## Alternative and exception flows

- In-progress external/ML calls may not stop instantly.
- If nothing matches, unrelated work is unchanged.

## Postconditions

- Targeted work ends or is requested to end with explicit `cancelled` semantics; unrelated terminal Jobs are unchanged.

## Security and privacy notes

- Cancellation/log output is sanitized; cleanup cannot remove canonical evidence of unrelated Jobs.

## Current evidence references

- `docs/03-manual-de-uso.md`
- `src/yt_transcriber_bot/application/pipeline/runner.py`
- `src/yt_transcriber_bot/infrastructure/telegram/bot_adapter.py`

## Requirement dimensions to derive

- cancellation scope
- cooperative cancellation
- queue mutation invariants
- cleanup
- operator feedback
