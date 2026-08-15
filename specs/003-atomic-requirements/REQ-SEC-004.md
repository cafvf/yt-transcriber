# REQ-SEC-004 — Centralized sanitization of disclosure paths

Version: **1.0.0**
Status: **Approved / Frozen**
Wave: **A**
Derived families: **SEC-SANITIZE**
Behavior/spec sources: **UC-010, UC-011, IC-001**
Dependencies: **REQ-SEC-002, REQ-SEC-003**

## Normative requirement

All operator-facing diagnostics, persisted operational errors, audit records and transport error messages SHALL use one coherent sanitization policy before crossing their disclosure boundary.

## Acceptance criteria

- AC-01: Tokens, cookies, authorization headers and API keys are redacted.
- AC-02: Provider request/response bodies, prompts and transcript payloads echoed by exceptions are omitted or safely summarized.
- AC-03: Application audit and last-error paths do not maintain divergent secret/payload sanitization rules.
- AC-04: If sanitization itself cannot safely process an error, the fallback is a generic safe message rather than raw original content.

## Required evidence

- shared sanitizer contract tests
- regression cases for Telegram, audit and last-error paths

## Brownfield deviation addressed

Current application sanitizer and execution-audit logger have duplicate policies.

## Scope guard

This requirement repairs or preserves the approved current baseline. It does not authorize semantic search, translation, an alternative ASR product feature, checkpoint resume, multi-user behavior, or knowledge-system integration.
