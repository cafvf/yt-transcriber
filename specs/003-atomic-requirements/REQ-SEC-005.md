# REQ-SEC-005 — Untrusted input containment

Version: **1.0.0**
Status: **Approved / Frozen**
Wave: **A**
Derived families: **SEC-INPUT**
Behavior/spec sources: **UC-001, UC-006, UC-008, UC-009, Constitution VII**
Dependencies: **REQ-SEC-003**

## Normative requirement

Operator-supplied URLs, filenames, media metadata, transcript/provider text and other external content SHALL be treated as untrusted data and SHALL not control filesystem scope, application policy, credential selection or unintended command/execution behavior.

## Acceptance criteria

- AC-01: Filesystem-derived names and paths are normalized/contained before use.
- AC-02: External/provider text cannot select a different configured endpoint, credential source or file target merely by appearing in content.
- AC-03: Malformed or unsupported source/media metadata fails explicitly without escaping configured storage boundaries.
- AC-04: Content used in prompts, logs or rendering remains data and cannot inject application-level configuration or command execution.

## Required evidence

- input-validation and path-containment tests
- malformed provider metadata regression tests
- prompt/render boundary tests

## Scope guard

This requirement repairs or preserves the approved current baseline. It does not authorize semantic search, translation, an alternative ASR product feature, checkpoint resume, multi-user behavior, or knowledge-system integration.
