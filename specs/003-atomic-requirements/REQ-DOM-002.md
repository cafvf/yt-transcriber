# REQ-DOM-002 — Explicit Job lifecycle state machine

Version: **1.0.0**
Status: **Approved / Frozen**
Wave: **A**
Derived families: **DOMAIN-JOB**
Behavior/spec sources: **UC-001, UC-003, SS-001, D-013, D-014**
Dependencies: **REQ-DOM-001**

## Normative requirement

`Job` SHALL enforce the approved semantic transition graph and terminal-state rules, rejecting impossible transitions rather than permitting arbitrary non-terminal state changes.

## Acceptance criteria

- AC-01: Legal normal path includes pending→acquiring→converting→transcribing→diarizing→rendering→delivering→completed, with the approved subtitle shortcut acquiring→rendering.
- AC-02: Cancellation is legal only in approved pre-delivery processing states.
- AC-03: `completed`, `delivery_failed`, `failed` and `cancelled` are terminal.
- AC-04: Same-state assignment is not treated as a semantic transition.
- AC-05: Legacy persisted `downloading` is decoded as semantic `acquiring` without destructive migration.

## Required evidence

- parameterized legal/illegal transition tests
- persistence compatibility tests

## Brownfield deviation addressed

Current `Job.transition_to` only prevents leaving terminal states.

## Scope guard

This requirement repairs or preserves the approved current baseline. It does not authorize semantic search, translation, an alternative ASR product feature, checkpoint resume, multi-user behavior, or knowledge-system integration.
