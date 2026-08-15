# 002 — System Requirement Tree

Version: **1.0.0**
Status: **Approved / Frozen; atomic requirements derived in ../003-atomic-requirements**
Derived from: **000-baseline v1.0.0** and **001-use-cases v1.0.1**
Reference date: **2026-08-15**

## Purpose

Define the complete requirement taxonomy and dependency structure for the current-system hardening milestone before individual atomic requirement documents are written.

The identifiers in this package are **requirement families / branches**, not atomic SHALL/MUST statements. Their purpose is to guarantee conceptual coverage, dependency coherence, traceability, and an explicit home for every current behavior and known baseline deviation before REQ authoring.

## Review result

Version 0.1.0 was cross-checked against:

- the ratified Constitution;
- all approved `000-baseline` specifications;
- the frozen `001-use-cases` model;
- current `main` code and current integration-test evidence.

That review found material blind spots in the draft tree and corrected them in 0.2.0. The corrected tree adds explicit families for transport, execution/queue orchestration, runtime policy, diarization, operational external I/O, media/staging data, cache/model data, canonical-data integrity, supply-chain trust, and untrusted-input handling.

The review also completed the previously required inventory of the 46 tests excluded from the default gate. See `EVIDENCE-INVENTORY.md` and `REVIEW.md`.

## Root taxonomy

```text
SYS-001
├── FUNC   functional capabilities and interaction contracts
├── DOMAIN domain language, lifecycle, invariants, provenance
├── ARCH   architecture boundaries, orchestration ownership, extension contracts
├── DATA   persistence, media/artifact lifecycle, canonical evidence, indexing, compatibility, backup
├── NFR    reliability, resource behavior, observability, maintainability/compatibility
├── SEC    authorization, secrets, privacy, sanitization, input/supply-chain/external trust, filesystem protection
└── OPS    startup recovery, retention, service operation, backup/restore, rollback, manual recovery, evidence
```

Testing methodology remains governed by the Constitution and `000-baseline/QUALITY.md`; tests are verification/evidence for requirements, not a separate product-requirement family.

## Gate rule

The corrected tree is approved/frozen as v1.0.0. Atomic derivation is recorded in `../003-atomic-requirements/`; changes to requirement-family coverage require a versioned amendment to this package.
