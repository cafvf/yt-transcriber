# SS-001 — Startup/restart reconciliation

Version: **1.0.0**
Status: **Approved / Frozen**

## Purpose

Restore a coherent durable Job/queue view after process interruption without claiming unsupported mid-step checkpoint resume.

## Trigger

Process startup.

## Required scenario

1. Inspect eligible persisted Jobs once for the startup instance.
2. Requeue `pending` Jobs with sufficient restart payload in deterministic oldest-first order.
3. Convert legacy/incomplete `pending` Jobs that cannot safely restart to `failed` with explicit reason.
4. Convert interrupted processing states to `failed`.
5. Convert interrupted `delivering` to terminal `delivery_failed`.
6. Never reopen terminal Jobs.
7. Reintroduce recoverable pending work into the in-memory sequential queue.

## Constraints

- No mid-ASR/diarization checkpoint resume is promised.
- Recovery metadata/logging is private and sanitized.
