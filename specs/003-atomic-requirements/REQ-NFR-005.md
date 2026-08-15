# REQ-NFR-005 — Cohesive, testable and reversible baseline refactoring

Version: **1.0.0**
Status: **Approved / Frozen**
Wave: **C**
Derived families: **NFR-MAINTAIN**
Behavior/spec sources: **Constitution II/X, QUALITY §§3-8**
Dependencies: **REQ-ARC-001, REQ-ARC-002**

## Normative requirement

Baseline repair SHALL reduce responsibility hotspots through small reversible changes protected by characterization, contract, architecture and regression tests, and SHALL not preserve or add abstractions without a demonstrated approved capability.

## Acceptance criteria

- AC-01: Telegram, summary and persistence hotspots are decomposed according to responsibility/contract rather than file size alone.
- AC-02: Empty speculative domain packages are removed unless a current approved contract requires them.
- AC-03: Generic `FileStorage` disappears when explicit replacement-capability coverage exists.
- AC-04: Refactors preserve frozen behavior unless an approved requirement classifies the current behavior as a defect or authorized hardening.

## Required evidence

- characterization/contract tests before affected refactors
- architecture tests
- reviewable incremental diffs

## Scope guard

This requirement repairs or preserves the approved current baseline. It does not authorize semantic search, translation, an alternative ASR product feature, checkpoint resume, multi-user behavior, or knowledge-system integration.
