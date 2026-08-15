# REQ-ARC-012 — Purpose-specific application-owned ports

Version: **1.0.0**
Status: **Approved / Frozen**
Wave: **B**
Derived families: **ARCH-PORTS**
Behavior/spec sources: **Constitution III, ARCHITECTURE §§4-5**
Dependencies: **REQ-ARC-001, REQ-SEC-008**

## Normative requirement

External capabilities required by application behavior SHALL cross narrow application-owned ports or equivalent application abstractions that express the capability needed rather than a provider API or generic filesystem surface.

## Acceptance criteria

- AC-01: Ports are owned in application-facing modules and can be implemented by test doubles without importing infrastructure.
- AC-02: Port parameters/results use application/domain concepts and exclude provider credentials or unrelated transport payloads.
- AC-03: A generic filesystem abstraction is not retained solely to avoid defining the actual capability required by a workflow.
- AC-04: Unused generic `FileStorage` is removed once all current consumers/capabilities have explicit replacement coverage.

## Required evidence

- port architecture/conformance tests
- capability-level contract tests

## Scope guard

This requirement repairs or preserves the approved current baseline. It does not authorize semantic search, translation, an alternative ASR product feature, checkpoint resume, multi-user behavior, or knowledge-system integration.
