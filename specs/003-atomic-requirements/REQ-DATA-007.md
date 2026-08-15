# REQ-DATA-007 — Reconstructible cache lifecycle

Version: **1.0.0**
Status: **Approved / Frozen**
Wave: **A**
Derived families: **DATA-CACHE**
Behavior/spec sources: **UC-012**
Dependencies: **REQ-DOM-004, REQ-SEC-006, REQ-SEC-007**

## Normative requirement

Model, tokenizer and other cache data classified as reconstructible SHALL have explicit owned scope and safe cleanup semantics independent of canonical transcript retention.

## Acceptance criteria

- AC-01: Cache roots are explicitly configured or otherwise deterministically owned by the application.
- AC-02: Clearing cache never deletes Job DB, transcript snapshots, Markdown, summaries, credentials or unrelated data.
- AC-03: Subsequent approved processing may rebuild or redownload reconstructible cache.
- AC-04: Cache cleanup does not modify the configured model/tokenizer trust policy.

## Required evidence

- cache containment/deletion tests
- configuration conformance tests

## Scope guard

This requirement repairs or preserves the approved current baseline. It does not authorize semantic search, translation, an alternative ASR product feature, checkpoint resume, multi-user behavior, or knowledge-system integration.
