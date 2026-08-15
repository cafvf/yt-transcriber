# UC-011 — Inspect the latest operational error

Version: **1.0.0**
Status: **Approved / Frozen**
Derived from: **000-baseline v1.0.0**
Reference date: **2026-08-15**

## Goal

Understand the latest relevant failure through sanitized diagnostics and determine whether preserved local artifacts are available for a separate operator recovery procedure.

## Primary actor

Authorized Operator

## Trigger

`/lasterror`.

## Preconditions

- The operator is authorized.
- Operational-error/job history persistence is available.

## Main success scenario

1. The latest relevant operational failure is selected according to current precedence/order.
2. Sanitized operation/context/error information is returned.
3. For `delivery_failed`, the system truthfully reports preserved artifact availability and only the recovery information allowed by security policy.

## Alternative and exception flows

- No recorded error is explicit.
- Missing artifact paths are not represented as recoverable.
- The system does not automatically resend or reopen the terminal Job.

## Postconditions

- Inspection is read-only with respect to terminal Job lifecycle. Manual recovery, if needed, belongs to OS-004.

## Security and privacy notes

- Error text, paths, titles, IDs, and artifact locations are private even after sanitization; secrets/prompts/transcript bodies echoed by exceptions are masked/removed.

## Current evidence references

- `docs/08-seguranca-e-segredos.md`
- `src/yt_transcriber_bot/application/services/last_error.py`

## Requirement dimensions to derive

- error precedence
- sanitization
- truthful artifact availability
- no implicit redelivery
