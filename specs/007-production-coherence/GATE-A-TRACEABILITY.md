# GATE-P07-A — Traceability

Version: **1.0.0**

| Requirement | Task | Use cases | Test range |
|---|---|---|---|
| REQ-P07-002 | TASK-P07-001 | UC-A001…A004 | TC-A001…A014 |
| REQ-P07-001 | TASK-P07-002 | UC-A005…A008 | TC-A015…A023 |
| REQ-P07-003 | TASK-P07-003 | UC-A009…A015 | TC-A024…A040 |
| REQ-P07-004 | TASK-P07-004 | UC-A016…A019 | TC-A041…A049 |
| REQ-P07-005, REQ-P07-006 | TASK-P07-005 | UC-A020…A023 | TC-A050…A058 |
| REQ-P07-010 | all Gate A tasks | UC-A024 | TC-A059…A060 |
| inherited domain/data truth | all | UC-A025…A027 | TC-A061…A070 |

## Gate A completion dependency

```text
TASK-P07-001
      ↓
TASK-P07-002
      ↓
TASK-P07-003
      ↓
TASK-P07-004
      ↓
TASK-P07-005
      ↓
cross-task conformance
      ↓
full Gate A quality checklist
      ↓
GATE-P07-A PASS
```

A later task may reveal that an earlier semantic decision is incomplete. The correction returns to the
owning task, and all affected Gate A tests are rerun.

## Compatibility traceability

Every compatibility assertion in Gate A must point to:

```text
COMPAT-ID
  → exact legacy surface
  → translation boundary
  → fixture/test ID
  → removal condition
```

No test may be labeled "compatibility" solely because it protects current source code.
