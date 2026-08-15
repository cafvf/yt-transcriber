# Baseline Specification Status

Baseline package: **1.0.0**
Constitution: **1.0.0 — Ratified**
Package status: **Approved**
Reference date: **2026-08-15**

## Review result

The pre-REQ baseline specification set has completed its internal consistency review.

No blocking specification-level decision remains. Remaining `RD-*`, `PD-*`, and `VD-*` items are deliberately deferred to requirement derivation, implementation planning, and verification respectively.

## Specification set

| Artifact | Status | Purpose |
|---|---|---|
| `../constitution.md` | Ratified 1.0.0 | Highest engineering/governance principles |
| `PRODUCT.md` | Approved 1.0.0 | Product identity, present scope, feature freeze |
| `ARCHITECTURE.md` | Approved 1.0.0 | Target boundaries, dependency direction, current deviations |
| `DOMAIN.md` | Approved 1.0.0 | Domain language, canonical transcript semantics, Job lifecycle/taxonomy |
| `DATA-AND-ARTIFACTS.md` | Approved 1.0.0 | Persistence/artifact ownership, provenance, retention, compatibility |
| `QUALITY.md` | Approved 1.0.0 (evidence inventory later fulfilled) | SDD+TDD quality model, test taxonomy, evidence rules |
| `SECURITY-AND-OPERATIONS.md` | Approved 1.0.0 | Information security, credential/data handling, recovery/operations |
| `DECISIONS.md` | Approved record | Consolidated baseline decisions |
| `OPEN-DECISIONS.md` | Approved deferred-decision register | Deferred requirement/planning/verification decisions |

## Material decisions closed in review

- specification is normative intent; brownfield code/tests are evidence;
- behavior/contract/invariant-driven TDD remains mandatory;
- hexagonal dependency direction is enforceable;
- credentials are boundary concerns and AI/support surfaces are disclosure surfaces;
- structured transcript snapshots are canonical machine-readable evidence;
- Markdown is canonical human-readable rendering;
- Job lifecycle has an explicit semantic transition graph;
- `acquiring` is the source-neutral semantic state while legacy serialized `downloading` may be preserved for compatibility;
- `delivery_failed` remains terminal in this baseline;
- one processing-fingerprint concept replaces overlapping signatures;
- ASR and text-generation application contracts must be provider-neutral at the appropriate boundary;
- Telegram is a transport adapter, not a parallel application layer;
- lifecycle persistence, transcript storage, indexing, and search have distinct ownership;
- external configuration compatibility is preserved while internal taxonomy may improve;
- standard backups exclude reusable credentials/authentication cookies by default;
- empty speculative domain packages and unused generic `FileStorage` are not target architecture.

## Approval effect

The package was explicitly approved on 2026-08-15 as **1.0.0 / Approved**. That approval closed the Constitution/baseline-specification stage. `001-use-cases` was subsequently approved/frozen and `002-requirements` is now the active approval gate. No implementation plan or task list is authorized before atomic requirements are derived and approved.
