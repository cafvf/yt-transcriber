# REQ-DATA-001 — Durable Job state and restart/delivery request context

Version: **1.0.0**
Status: **Approved / Frozen**
Wave: **A**
Derived families: **DATA-JOB**
Behavior/spec sources: **UC-001, SS-001, DD-007**
Dependencies: **REQ-DOM-002, REQ-DOM-005, REQ-SEC-003**

## Normative requirement

Persistence SHALL durably associate each Job with the minimum source/request/provenance/routing state needed for history and restart/delivery semantics while keeping transport-specific routing outside the pure Job domain model.

## Acceptance criteria

- AC-01: Job identity, lifecycle and recorded provenance survive restart.
- AC-02: Source recovery data is source-specific; a non-empty string alone is not sufficient proof of recoverability.
- AC-03: Telegram chat routing may be persisted as application request/delivery context but is not an intrinsic pure-domain Job property.
- AC-04: No full Telegram/provider payload is persisted merely as restart state.

## Required evidence

- SQLite round-trip/migration integration tests
- startup recovery tests
- architecture test for domain transport leakage

## Brownfield deviation addressed

`Job` currently contains `requested_chat_id` and overloads `source_url` for URL/local-path semantics.

## Scope guard

This requirement repairs or preserves the approved current baseline. It does not authorize semantic search, translation, an alternative ASR product feature, checkpoint resume, multi-user behavior, or knowledge-system integration.
