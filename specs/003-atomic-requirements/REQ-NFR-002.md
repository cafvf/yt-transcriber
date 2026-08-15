# REQ-NFR-002 — Bounded resource consumption and external waits

Version: **1.0.0**
Status: **Approved / Frozen**
Wave: **C**
Derived families: **NFR-RESOURCE**
Behavior/spec sources: **PRODUCT §7, UC-001, UC-007, UC-009**
Dependencies: **REQ-DATA-002, REQ-DATA-006, REQ-DATA-007, REQ-DATA-010**

## Normative requirement

The baseline SHALL bound queue occupancy, media/duration/artifact/log/cache/token operations and external waits so an approved request cannot consume unbounded application resources.

## Acceptance criteria

- AC-01: Queue capacity is configured and enforced before acceptance.
- AC-02: Unknown duration cannot bypass the configured maximum-duration protection.
- AC-03: Subprocess/network/provider waits use finite timeout and/or cooperative cancellation semantics where the underlying operation permits.
- AC-04: Summary input/output/token/chunk budgets are configured and bounded.
- AC-05: Operational logs, cache and retention-managed storage have explicit bounded lifecycle policies.

## Required evidence

- resource-limit tests
- timeout/cancellation tests
- summary budget tests
- retention/cache/log lifecycle tests

## Scope guard

This requirement repairs or preserves the approved current baseline. It does not authorize semantic search, translation, an alternative ASR product feature, checkpoint resume, multi-user behavior, or knowledge-system integration.
