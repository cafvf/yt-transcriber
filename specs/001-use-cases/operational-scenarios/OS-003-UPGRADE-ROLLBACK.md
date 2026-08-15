# OS-003 — Upgrade and rollback

Version: **1.0.0**
Status: **Approved / Frozen**

## Goal

Upgrade from a known-good deployment and return to the previous known-good state when validation fails.

## Scenario

Record source commit/version, perform controlled upgrade, validate service and key operator checks, exercise rollback using the documented mechanism, and validate service/data state again. Evidence must be reproducible and sanitized.
