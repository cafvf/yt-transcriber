# REQ-ARC-011 — Composition-root ownership of concrete providers and credentials

Version: **1.0.0**
Status: **Approved / Frozen**
Wave: **B**
Derived families: **ARCH-COMPOSITION**
Behavior/spec sources: **Constitution III/V, D-023**
Dependencies: **REQ-ARC-012, REQ-ARC-010, REQ-SEC-002, REQ-SEC-008**

## Normative requirement

Composition/runtime SHALL select and configure concrete Telegram, YouTube, persistence, ML, tokenizer/text-generation and operational adapters, injecting only application-facing capabilities inward and retaining provider credentials at the edge.

## Acceptance criteria

- AC-01: Runtime wiring has one clear composition owner.
- AC-02: Provider tokens, cookies and API keys are resolved at the edge and are not forwarded through generic domain/application requests.
- AC-03: Optional capabilities can be disabled without fake credentials.
- AC-04: Composition smoke tests verify the configured object graph without external network calls where practical.

## Required evidence

- composition-root tests
- architecture credential scan

## Scope guard

This requirement repairs or preserves the approved current baseline. It does not authorize semantic search, translation, an alternative ASR product feature, checkpoint resume, multi-user behavior, or knowledge-system integration.
