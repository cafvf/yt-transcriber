# F0 — Executable Baseline and Frozen-Interface Characterization

Task: `TASK-P01-000`
Implementation date: **2026-08-15**
Baseline revision: `5266d01b660398d0ff25c1bff01eb287114f0d7d`
Baseline commit: `docs: establish SDD architecture baseline`
Status: **Verified / Closed**

## 1. Purpose

F0 records the exact pre-remediation brownfield starting point and strengthens
characterization of the frozen interaction surface without changing product
behavior. It is support/characterization work only.

## 2. Starting repository state

Immediately after publishing the SDD baseline, local `main` and `origin/main`
were both at:

```text
5266d01b660398d0ff25c1bff01eb287114f0d7d
```

The reported working-tree status was:

```text
## main...origin/main
```

No productive remediation change is included in that baseline commit.

## 3. Hosted reproducibility evidence at the baseline revision

GitHub Actions CI run `31901072522` for the exact baseline revision completed
successfully on 2026-08-15.

Observed jobs:

- Tests and lint — Python 3.11: success;
- Tests and lint — Python 3.12: success;
- Security scans: success.

The Python 3.12 job recorded:

```text
collected 749 items / 46 deselected / 703 selected
703 passed, 46 deselected
Ruff lint: passed
Ruff format check: passed
mypy: Success: no issues found in 100 source files
```

The security job recorded successful pre-commit, project secret scan, and
Gitleaks full scan.

The approved QUALITY baseline also records 79% branch-aware global coverage.
The current CI workflow does not itself rerun/report that coverage value, so the
local F0 verification command below must preserve the coverage observation as
separate evidence rather than infer it from CI.

## 4. Frozen-interface characterization map

The current compatibility surface is discoverable at these executable and
normative locations:

| Concern | Characterization/evidence location |
|---|---|
| Registered Telegram commands/aliases and startup ordering | `tests/unit/test_entrypoint_command_registration.py` |
| Public `/help` command inventory and descriptions | `tests/unit/infrastructure/telegram/test_help_text.py` |
| Registration ↔ help frozen-surface conformance | `tests/conformance/test_current_interface.py` |
| External configuration/env compatibility | `tests/unit/application/test_config.py` |
| Normative current interaction conformance | `specs/001-use-cases/interface-conformance/IC-001-CURRENT-INTERFACE.md` |
| Default pytest marker policy | `pyproject.toml` |
| All 46 gated integration tests and their classified purpose | `specs/002-requirements/EVIDENCE-INVENTORY.md` |

The new conformance test intentionally observes registered command behavior via
a fake PTB application instead of asserting source-code formatting. It freezes
the current command set and alias-handler equivalence while allowing later
internal refactoring.

## 5. Local verification evidence

The operator reran the F0 characterization and full local gate on 2026-08-15.
Observed results:

```text
Targeted F0 characterization: 44 passed
Default suite: 753 collected / 46 deselected / 707 passed
Integration inventory: exactly 46 integration-marked tests
Branch-aware global coverage: 79%
Ruff lint/format: green after the F0-only lint correction
mypy/compile/pre-commit/security scans/diff check: green
```

This closes `TASK-P01-000`. The classified set of 46 integration tests remains
the compatibility fact; global test counts may grow as later phases add evidence.

## 6. Scope confirmation

F0 changes no production behavior and no frozen normative document. It adds:

- execution-phase evidence;
- the operational F0–F7 execution view;
- frozen-interface conformance tests.

Security remediation begins only in F1 (`TASK-P01-001`).
