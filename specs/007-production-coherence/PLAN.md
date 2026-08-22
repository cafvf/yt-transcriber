# PLAN-007 — Production Coherence & Distribution

Version: **1.0.0**
Status: **Approved for execution**
Baseline audited: **6f77d24f2c82d4748fd777056325f629c6fdf27a**

## Goal
Converge the private single-operator bot into a semantically coherent, safely configurable, cleanly
installable and distributable release candidate without architectural rewrite or unrelated features.

## P07-A — Canonical taxonomy
Owns MediaMetadata convergence, typed languages, truthful audio-track selection, source-neutral
duration, processing fingerprint, artifact typing and compatibility isolation.

Exit: no known semantic contradiction remains in canonical domain/application naming.

## P07-B — Error contract and boundaries
Owns stable error semantics, safe provider exception mapping, canonical Markdown writer integration,
remaining governed application I/O hotspots and regression conformance checks.

Exit: stable provider-neutral operational errors and no newly expanded direct-I/O debt.

## P07-C — Configuration, packaging and distribution
Owns one production env-file policy outside repo, credential/config convergence, runtime/dev
dependency separation, YouTube JS/ejs prerequisites, package build, clean install and preflight.

Exit: clean production install reaches deterministic health/preflight without dev tooling.

## P07-D — Documentation and onboarding
Owns root README rewrite and reconciliation of install/security/runbook/readiness docs after A-C.

Exit: current operator documentation agrees with implementation and itself.

## P07-E — Release gate
Owns exact candidate revision, lint/format/type/tests/conformance/integration/security/build/clean
install, controlled YouTube smoke, operational evidence where relevant, checksums and final decision.

Exit: PASS, PASS WITH RESERVATION only for non-critical limitations, or BLOCKED.

## Compatibility constraint
No compatibility item may be introduced or retained without a `COMPAT-*` record and evidence.

## Handoff
Only after P07-E passes may feature work resume; backend/multilingual/translation remain ahead of
Obsidian-specific note generation.

<!-- PLAN-007:GATE-A:STATUS:2026-08-21 -->
## Execution status — 2026-08-21

- **GATE-P07-A — Truthful Canonical Semantics: CLOSED / PASS**.
- Canonical implementation: `cd5f71d` (`refactor: complete PLAN-007 canonical taxonomy`).
- Closure evidence: [`GATE-A-CLOSURE.md`](GATE-A-CLOSURE.md).
- Next implementation target: **GATE-P07-B**.

<!-- PLAN-007:GATE-B:STATUS:2026-08-22 -->
## Execution status — 2026-08-22

- **GATE-P07-B — Safe Boundaries and Operational Error Semantics: CLOSED / PASS**.
- Canonical implementation: `2bc2041` (`refactor: establish PLAN-007 safe operational boundaries`).
- Closure evidence: [`GATE-B-CLOSURE.md`](GATE-B-CLOSURE.md).
- Gate A remains inherited and green on the Gate B candidate.
- Next implementation target: **GATE-P07-C — Distributable Runtime and Configuration**.
