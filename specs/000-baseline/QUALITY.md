# Baseline Quality Specification

Version: **1.0.1**
Status: **Approved**
Baseline date: **2026-08-15**

## 1. Quality model

The project keeps TDD and adds SDD upstream.

SDD defines intent and acceptance boundaries. TDD provides incremental executable evidence.

```text
SPECIFICATION
    -> ACCEPTANCE BOUNDARY
    -> TEST RED
    -> IMPLEMENTATION GREEN
    -> REFACTOR
    -> CONFORMANCE
```

Implementation plans/tasks are intentionally deferred.

## 2. Current executable baseline

On 2026-08-15 the local baseline completed dependency sync, Ruff lint, Ruff format check, mypy, default pytest selection, branch-aware coverage, local secret scanning, Gitleaks, and `git diff --check`.

Observed result:

- 749 tests collected;
- 703 selected and passed;
- 46 deselected;
- 79% global coverage.

This is the reference baseline for the specification/refactoring milestone.

## 3. Coverage philosophy

Global coverage is not a standalone target.

Coverage is interpreted by risk:

- domain invariants → strong direct coverage;
- application orchestration → strong behavioral coverage;
- ports → contract coverage where applicable;
- persistence → integration coverage of real semantics;
- external ML/network adapters → gated integration/compatibility tests where needed;
- composition/runtime → targeted smoke/conformance checks;
- architecture → architecture tests, not line coverage.

## 4. Target test taxonomy

```text
tests/
├─ unit/
│  ├─ domain/
│  ├─ application/
│  └─ infrastructure/
├─ contract/
├─ integration/
├─ e2e/
├─ architecture/
└─ conformance/
```

Existing tests need not move for cosmetic reasons.

## 5. Characterization and regression

Before structural refactoring, characterization tests protect intended unchanged behavior.

Characterization does not bless undesirable behavior. Suspicious behavior is classified as intended baseline, defect, obsolete behavior, or unresolved decision.

Every reproducible behavior defect should gain a regression test at the lowest useful level demonstrating the violated contract.

## 6. Contract tests

When multiple adapters implement the same port, shared contract tests should validate common semantics where practical.

## 7. Architecture tests

Architecture tests must enforce at least:

- domain does not import infrastructure;
- application does not import infrastructure;
- provider-specific credentials do not appear in domain/application contracts unless explicitly approved;
- dependency direction matches the architecture specification.

## 8. Conformance tests

Conformance tests keep executable behavior aligned with normative documents.

Existing documentation-consistency tests are a useful seed.

Future conformance may cover command registration, status vocabulary, configuration catalog, schema/document compatibility, and later requirement identifiers.

## 9. Marked tests

The 46 deselected tests are not automatically debt.

The pre-REQ inventory required by v1.0.0 was completed on 2026-08-15 and is recorded in `../002-requirements/EVIDENCE-INVENTORY.md`: all 46 are integration-marked tests covering SQLite persistence/migration, textual-search persistence, the non-target generic LocalFileStorage abstraction, real ffmpeg behavior, and file-backed startup recovery.

Later atomic requirements must identify which of that evidence remains required in default versus environment-specific gates. This patch records completion of the already-approved evidence obligation; it does not change the quality policy.

## 10. Hotspots

Coverage indicates unequal risk. Components combining high responsibility and weak coverage deserve review, particularly the current SQLAlchemy job repository and large Telegram adapter.

Low coverage in a real external backend may be acceptable when reliable execution requires an environment-gated test, but that rationale must be explicit.

## 11. Quality gates

A change is not validated merely because `pytest` passes.

Relevant gates may include lint, format, typing, unit, architecture, contract, integration, security, migration, and operational evidence.

Before commit/release, report what ran and what could not run due to environment.

## 12. No quality theater

Avoid tests written only to inflate coverage, assertions tied to private implementation, mocks that reproduce third-party internals, unenforced architecture documents, declaring operational readiness from helper-script tests alone, and treating historical passing baselines as proof for later HEADs.
