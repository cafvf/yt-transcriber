# REQ-ARC-001 — Mechanically enforced dependency direction

Version: **1.0.0**
Status: **Approved / Frozen**
Wave: **B**
Derived families: **ARCH-BOUNDARY**
Behavior/spec sources: **Constitution III, ARCHITECTURE §3**
Dependencies: **upstream approved specifications only**

## Normative requirement

The approved layer dependency direction SHALL be mechanically enforced so domain remains independent of application/infrastructure and application remains independent of concrete infrastructure.

## Acceptance criteria

- AC-01: Domain runtime code imports only approved stdlib/domain dependencies.
- AC-02: Application runtime code does not import infrastructure modules.
- AC-03: Architecture checks execute in the default quality gate.
- AC-04: Direct stdlib access to external I/O from application is governed by purpose-specific boundary requirements rather than used as a loophole around the dependency rule.

## Required evidence

- architecture dependency tests in the default gate

## Scope guard

This requirement repairs or preserves the approved current baseline. It does not authorize semantic search, translation, an alternative ASR product feature, checkpoint resume, multi-user behavior, or knowledge-system integration.
