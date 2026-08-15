# REQ-DATA-010 — Completed-Job retention policy and canonical preservation

Version: **1.0.0**
Status: **Approved / Frozen**
Wave: **A**
Derived families: **DATA-RETENTION**
Behavior/spec sources: **SS-002, DATA-AND-ARTIFACTS §8**
Dependencies: **REQ-DATA-002, REQ-DATA-003, REQ-SEC-007**

## Normative requirement

Completed-Job retention SHALL classify which artifact classes are eligible for automatic removal and SHALL preserve the canonical structured transcript and Markdown required by approved baseline history, rename and export behavior.

## Acceptance criteria

- AC-01: The configured retention count/policy selects eligible completed Jobs deterministically.
- AC-02: Canonical structured snapshot and Markdown are not removed by completed-Job volatile retention.
- AC-03: Only artifact classes explicitly classified as volatile/retention-eligible are removed.
- AC-04: Retention eligibility is based on Job/artifact ownership and policy, not arbitrary unrelated filesystem age.

## Required evidence

- retention policy tests
- artifact-classification conformance tests

## Scope guard

This requirement repairs or preserves the approved current baseline. It does not authorize semantic search, translation, an alternative ASR product feature, checkpoint resume, multi-user behavior, or knowledge-system integration.
