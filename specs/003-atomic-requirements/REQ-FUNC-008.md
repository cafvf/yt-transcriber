# REQ-FUNC-008 — Generate transcript exports from canonical evidence

Version: **1.0.0**
Status: **Approved / Frozen**
Wave: **D**
Derived families: **FUNC-EXPORT**
Behavior/spec sources: **UC-008**
Dependencies: **REQ-DATA-003, REQ-DATA-005, REQ-ARC-006, REQ-SEC-003**

## Normative requirement

The operator SHALL be able to generate supported transcript export formats from canonical structured evidence and current speaker aliases without changing canonical transcript state.

## Acceptance criteria

- AC-01: TXT, JSON, SRT and VTT outputs are generated from structured canonical evidence rather than by parsing Markdown.
- AC-02: Current persisted speaker aliases are reflected where the export format contains speaker text/labels.
- AC-03: Unsupported format or history position is reported explicitly.
- AC-04: Missing structured evidence is reported explicitly and is not reconstructed from Markdown or media.

## Required evidence

- export-format tests
- speaker-alias export tests
- missing-evidence tests

## Scope guard

This requirement repairs or preserves the approved current baseline. It does not authorize semantic search, translation, an alternative ASR product feature, checkpoint resume, multi-user behavior, or knowledge-system integration.
