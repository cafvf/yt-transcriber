# REQ-NFR-006 — External behavior and data compatibility during baseline repair

Version: **1.0.0**
Status: **Approved / Frozen**
Wave: **C**
Derived families: **NFR-COMPAT**
Behavior/spec sources: **DD-003, DD-004**
Dependencies: **REQ-DATA-008**

## Normative requirement

Baseline repair SHALL preserve frozen commands, aliases, approved operator configuration and readable historical data unless an approved versioned requirement explicitly changes an unsupported or unsafe surface.

## Acceptance criteria

- AC-01: Existing approved environment variables remain accepted.
- AC-02: Legacy DB and snapshot data remain readable.
- AC-03: Frozen command aliases remain registered.
- AC-04: Internal Python names may change without public compatibility promise.
- AC-05: The private-chat-only hardening is documented as an intentional narrowing of an otherwise unspecified group/shared-chat surface.

## Required evidence

- compatibility/conformance tests
- migration tests
- documentation change log

## Scope guard

This requirement repairs or preserves the approved current baseline. It does not authorize semantic search, translation, an alternative ASR product feature, checkpoint resume, multi-user behavior, or knowledge-system integration.
