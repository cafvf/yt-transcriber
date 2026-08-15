# REQ-FUNC-006 — Rename and merge speakers from canonical evidence

Version: **1.0.0**
Status: **Approved / Frozen**
Wave: **D**
Derived families: **FUNC-EDIT**
Behavior/spec sources: **UC-006**
Dependencies: **REQ-DATA-001, REQ-DATA-003, REQ-DATA-004, REQ-DATA-005, REQ-DATA-011, REQ-ARC-006**

## Normative requirement

The operator SHALL be able to persist valid speaker aliases/merges and re-render Markdown and affected textual-search state from canonical structured transcript evidence without rerunning ASR/diarization or mutating canonical segment identity.

## Acceptance criteria

- AC-01: Only existing speaker labels and non-empty alias values are accepted.
- AC-02: Assigning the same alias to multiple labels may represent an intentional merge.
- AC-03: Alias state persists durably with the Job/application record.
- AC-04: Missing canonical structured evidence fails explicitly; Markdown is not parsed as a substitute.
- AC-05: Affected textual-search state is explicitly refreshed.

## Required evidence

- rename domain/application tests
- rerender tests
- search refresh tests

## Scope guard

This requirement repairs or preserves the approved current baseline. It does not authorize semantic search, translation, an alternative ASR product feature, checkpoint resume, multi-user behavior, or knowledge-system integration.
