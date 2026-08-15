# SS-002 — Retention of volatile artifacts

Version: **1.0.0**
Status: **Approved / Frozen**

## Purpose

Bound volatile media/log storage while preserving evidence required by current history, rename, export, and recovery contracts.

## Required scenario

1. Select eligible old completed Jobs according to current FIFO/count policy.
2. Delete only artifact classes designated volatile.
3. Preserve canonical Markdown and structured transcript snapshots required by current guarantees.
4. Keep persisted artifact references truthful after deletion.
5. Sanitize cleanup failures and avoid collateral deletion.

Retention is both an operational/storage policy and a privacy control; it must not silently destroy canonical evidence still promised by the baseline.
