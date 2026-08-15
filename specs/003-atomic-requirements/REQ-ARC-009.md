# REQ-ARC-009 — Operational policy separated from external I/O mechanisms

Version: **1.0.0**
Status: **Approved / Frozen**
Wave: **B**
Derived families: **ARCH-OPS**
Behavior/spec sources: **UC-010, UC-011, SS-002**
Dependencies: **REQ-ARC-012, REQ-DATA-006, REQ-SEC-007**

## Normative requirement

Health, error-selection, retention and related operational policy SHALL remain application behavior while filesystem, network, subprocess and log mechanisms are accessed through explicit purpose-specific probes/stores/adapters rather than direct external I/O in application policy code.

## Acceptance criteria

- AC-01: Healthcheck application logic consumes injected probe results/capabilities.
- AC-02: Operational-error persistence is behind a purpose-specific application-owned store/capability.
- AC-03: Retention requests deletion through owned artifact/storage capabilities.
- AC-04: Using stdlib filesystem/network/subprocess APIs directly does not bypass the application/infrastructure boundary.

## Required evidence

- architecture tests for application I/O hotspots
- application tests with fake probes/stores

## Scope guard

This requirement repairs or preserves the approved current baseline. It does not authorize semantic search, translation, an alternative ASR product feature, checkpoint resume, multi-user behavior, or knowledge-system integration.
