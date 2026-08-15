# UC-010 — Inspect runtime health

Version: **1.0.0**
Status: **Approved / Frozen**
Derived from: **000-baseline v1.0.0**
Reference date: **2026-08-15**

## Goal

Assess whether the private runtime is ready for supported operations and identify actionable configuration/dependency problems.

## Primary actor

Authorized Operator

## Trigger

`/healthcheck`.

## Preconditions

- The operator is authorized.

## Main success scenario

1. Safe health dimensions are probed.
2. Blocking/advisory conditions are classified as applicable.
3. Compact sanitized diagnostics are returned.

## Alternative and exception flows

- Optional capability absence is distinguished from blockers when appropriate.
- Probe failures become sanitized health findings.

## Postconditions

- Health inspection does not mutate Job/transcript state except benign probe mechanics later made explicit.

## Security and privacy notes

- Secret values are never returned; sanitized diagnostics remain private and minimize paths/identifiers.

## Current evidence references

- `docs/08-seguranca-e-segredos.md`
- `src/yt_transcriber_bot/application/services/healthcheck.py`

## Requirement dimensions to derive

- health dimension catalog
- severity
- secret-safe output
- probe side effects
- secret-file permission policy
