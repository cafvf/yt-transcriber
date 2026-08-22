# GATE-P07-A — Failure and Pre-Delivery Checklist

Version: **1.0.0**
Status: **Normative for Gate A delivery**

This document specializes the project pre-delivery error checklist for Gate A.

## F-A01 — Artifact integrity

For every ZIP/patch delivered:

- opens and extracts completely;
- expected files only;
- SHA-256 generated;
- included checksum manifest verifies.

**Failure:** BLOCKED.

## F-A02 — Git scope/integrity

Record exact HEAD/base, `git status --short --branch`, `git diff --check`, staged diff and intentional
file list.

Unexpected dirty state or whitespace errors are BLOCKED.

## F-A03 — Syntax/import integrity

Gate A renames types/modules, so broken imports are a primary risk.

Run compile/import checks and targeted tests after every migration increment.

Broken import/syntax: BLOCKED.

## F-A04 — Ruff lint and formatting

Run:

```bash
uv run ruff check .
uv run ruff format --check .
```

Any failure: BLOCKED unless the tool itself is unavailable for an explicitly diagnosed environmental
reason; before Gate A closure it must execute successfully.

## F-A05 — Mypy

Run:

```bash
uv run mypy src
```

Gate A is type-heavy. Any mypy error is BLOCKED; do not suppress merely to preserve old string types.

## F-A06 — Tests

Required:

- focused tests for the current increment;
- Gate A semantic/conformance tests;
- inherited architecture/conformance tests;
- relevant persistence compatibility tests;
- full default `uv run pytest` before Gate A PASS.

A focused green subset cannot override a full-suite regression.

## F-A07 — Architecture

Verify no:

- domain→application/infrastructure import;
- application→infrastructure import;
- concrete provider leaked into core;
- provider credential leaked into generic contracts;
- allowlist enlarged without approved exception.

Any violation: BLOCKED.

## F-A08 — Taxonomy/semantic errors

This is Gate A's highest-risk checklist.

Search for:

- two names for one canonical concept;
- one name with contradictory meanings;
- misleading booleans;
- raw strings replacing existing typed values;
- Video/Media drift;
- config_signature/processing_fingerprint drift;
- source-specific vocabulary in source-neutral contracts;
- units omitted where ambiguity exists;
- persistence representation treated as domain vocabulary;
- duplicate mutable fields representing derivable facts.

Any unexplained occurrence prevents Gate A PASS.

## F-A09 — Error/exception regression

Gate B will introduce the stable error contract, but Gate A must not worsen current behavior.

Verify that semantic migrations do not:

- swallow download/policy exceptions;
- turn failed original-track selection into success;
- replace explicit unknown with a default;
- change existing business rejection behavior accidentally.

## F-A10 — Security/secrets

Run the project controls:

```bash
uv run pre-commit run --all-files
python3 scripts/security/scan_secrets.py --all
python3 scripts/security/gitleaks_if_available.py --all
```

A scanner that fails to execute is not a pass.

Also inspect for `.env`, cookies, databases, logs, transcripts, media and token-like fixtures.

## F-A11 — Documentation/spec conformance

Gate A documentation must match canonical code after implementation. Do not rewrite historical reports.

User-facing README rewrite waits for Gate D, but newly canonical terminology in normative PLAN-007
documents must not contradict source.

## F-A12 — Clean installation

Full clean-install proof is introduced by Gate C, so it is **not a Gate A closure requirement** unless
Gate A unexpectedly changes packaging/import-resource behavior.

However, Gate A must preserve existing supported imports and startup paths; module renames receive
import regression coverage.

## F-A13 — Operational/runtime evidence

systemd/host rehearsal is not normally required for Gate A.

A controlled YouTube adapter smoke may be recorded when available because TASK-P07-001 changes actual
selection behavior, but it does not replace unit/contract tests and is not mandatory if provider/network
access is unavailable.

## F-A14 — Gate completion report

Gate A cannot be marked PASS without:

- candidate SHA;
- files changed;
- compatibility entries retained/removed;
- commands and exit codes;
- focused/full test totals;
- security results;
- checks not run and why;
- exact unresolved reservations (normally none for correctness/architecture/security).

## Gate A decision

**PASS:** every applicable F-A item and TC-A001…TC-A070 contract applicable to the chosen implementation
passes on one exact revision.

**BLOCKED:** correctness, typing, regression, architecture, taxonomy, compatibility, security or
artifact integrity fails or cannot be trusted.

There is no internal Gate A `PASS WITH RESERVATION` for such defects.

<!-- PLAN-007:GATE-A:QUALITY-EVIDENCE:2026-08-21 -->
## Executed closure evidence — 2026-08-21

- **Pre-commit cumulative Gate A validation:** 21 PASS, 0 FAIL, 0 SKIP.
- **Independent post-commit validation:** 12 PASS, 0 FAIL.
- Ruff lint/format: PASS.
- production mypy: PASS, 143 source files, zero issues.
- complete conformance: 157 passed.
- Gate A SQLite integration with explicit marker override: 2 passed.
- configured pytest suite: 994 passed, 37 deselected.
- pre-commit: PASS.
- Gitleaks: no leaks found.
- committed working tree: clean.

Detailed evidence and closure interpretation: [`GATE-A-CLOSURE.md`](GATE-A-CLOSURE.md).
