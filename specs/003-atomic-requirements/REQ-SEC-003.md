# REQ-SEC-003 — Private-data classification and minimization

Version: **1.0.0**
Status: **Approved / Frozen**
Wave: **A**
Derived families: **SEC-PRIVACY**
Behavior/spec sources: **Constitution VI, SECURITY-AND-OPERATIONS §8**
Dependencies: **upstream approved specifications only**

## Normative requirement

The system SHALL treat media, transcripts, speaker aliases, queries/results, indexes, transport/provider identifiers, filesystem paths, logs, derivatives and backups as private data and SHALL disclose or persist only the minimum required for the approved operation.

## Acceptance criteria

- AC-01: Search, diagnostic and queue outputs omit transcript bodies unless the invoked operation explicitly requests transcript content.
- AC-02: Private filesystem paths and provider/transport identifiers are omitted when a stable opaque identifier or availability flag is sufficient.
- AC-03: Derived artifacts inherit private classification from their canonical source.
- AC-04: Sanitized data remains private by default and is not reclassified as public merely because secrets were removed.

## Required evidence

- privacy-focused unit tests
- review checklist for new persistence/transport outputs

## Scope guard

This requirement repairs or preserves the approved current baseline. It does not authorize semantic search, translation, an alternative ASR product feature, checkpoint resume, multi-user behavior, or knowledge-system integration.
