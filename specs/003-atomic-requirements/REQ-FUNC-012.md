# REQ-FUNC-012 — Command, help and documentation conformance

Version: **1.0.0**
Status: **Approved / Frozen**
Wave: **D**
Derived families: **FUNC-INTERFACE**
Behavior/spec sources: **IC-001**
Dependencies: **REQ-FUNC-001, REQ-FUNC-002, REQ-FUNC-003, REQ-FUNC-004, REQ-FUNC-005, REQ-FUNC-006, REQ-FUNC-007, REQ-FUNC-008, REQ-FUNC-009, REQ-FUNC-010, REQ-FUNC-011, REQ-FUNC-013, REQ-FUNC-014, REQ-NFR-006**

## Normative requirement

Registered commands, aliases, help/manual text, product naming and current/future documentation SHALL conform to the approved baseline without claiming unimplemented features or preserving obsolete YouTube-only product identity.

## Acceptance criteria

- AC-01: Command registration matches the documented current command set and aliases.
- AC-02: Help/manual do not advertise future semantic search, translation or other frozen-out functionality.
- AC-03: Roadmap does not list already-shipped CI/current capabilities as future work.
- AC-04: Package/README description reflects the current YouTube-plus-Telegram-media product scope.
- AC-05: Historical gate reports remain historical rather than being rewritten as current normative specifications.

## Required evidence

- command-registration tests
- documentation-conformance tests
- roadmap/current-capability cross-check

## Scope guard

This requirement repairs or preserves the approved current baseline. It does not authorize semantic search, translation, an alternative ASR product feature, checkpoint resume, multi-user behavior, or knowledge-system integration.
