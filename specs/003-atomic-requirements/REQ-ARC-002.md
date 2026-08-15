# REQ-ARC-002 — Application workflow ownership and thin Telegram transport

Version: **1.0.0**
Status: **Approved / Frozen**
Wave: **B**
Derived families: **ARCH-APP, ARCH-TRANSPORT**
Behavior/spec sources: **ARCHITECTURE §9.2, UC-001..UC-012**
Dependencies: **REQ-ARC-001, REQ-ARC-012, REQ-SEC-001**

## Normative requirement

Portable workflow decisions SHALL be owned by application use cases/services while Telegram infrastructure is limited to Telegram protocol parsing/presentation, Telegram-specific inline state, boundary authorization/audience enforcement and send mechanics.

## Acceptance criteria

- AC-01: Submission/dedup/cancel/history/search/rename/summary/export/retention/delivery-result policy can be exercised without Telegram classes.
- AC-02: Telegram callback/UI state that has no portable business meaning may remain in the adapter.
- AC-03: History selection rules are not owned solely by `infrastructure.telegram`.
- AC-04: Telegram adapter dependencies are application capabilities/use cases rather than a parallel concrete service graph.

## Required evidence

- application tests without Telegram classes
- architecture/import tests
- adapter conformance tests

## Brownfield deviation addressed

`TelegramBotAdapter` and `HistoryCollaboration` currently own substantial application policy.

## Scope guard

This requirement repairs or preserves the approved current baseline. It does not authorize semantic search, translation, an alternative ASR product feature, checkpoint resume, multi-user behavior, or knowledge-system integration.
