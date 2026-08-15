# REQ-FUNC-009 — Inspect runtime health safely

Version: **1.0.0**
Status: **Approved / Frozen**
Wave: **D**
Derived families: **FUNC-DIAG**
Behavior/spec sources: **UC-010, DD-002**
Dependencies: **REQ-ARC-009, REQ-DATA-006, REQ-NFR-003, REQ-SEC-004, REQ-NFR-007**

## Normative requirement

The authorized operator SHALL be able to run a bounded, side-effect-minimized health assessment that classifies blocking/advisory conditions and returns sanitized actionable diagnostics without revealing secrets.

## Acceptance criteria

- AC-01: Checks cover the current required runtime, configuration, dependency, storage and summary dimensions through approved probes.
- AC-02: Optional capability absence may be classified as warning rather than blocker when the baseline can otherwise operate.
- AC-03: Probe failure becomes a sanitized finding rather than a raw exception.
- AC-04: Healthcheck is not required to discover the systemd secret-file path or permissions; host preflight owns that evidence.

## Required evidence

- healthcheck application tests with fake probes
- sanitization tests
- async responsiveness test

## Scope guard

This requirement repairs or preserves the approved current baseline. It does not authorize semantic search, translation, an alternative ASR product feature, checkpoint resume, multi-user behavior, or knowledge-system integration.
