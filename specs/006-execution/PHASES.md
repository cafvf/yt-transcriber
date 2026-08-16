# Implementation Phases

Status: **Active execution view**
Source: approved/frozen `005-tasks` v1.0.0

These phases are an operational grouping only. They do not change task
ownership, task dependencies, requirement ownership, or PLAN exit gates.

| Phase | Purpose | Approved task range |
|---|---|---|
| F0 | Executable baseline and frozen-interface characterization | `TASK-P01-000` |
| F1 | Security guardrails | `TASK-P01-001..008` |
| F2 | Domain truth and canonical data consistency | `TASK-P02-001..013` |
| F3 | Hexagonal boundaries and provider seams | `TASK-P03-001..014` |
| F4 | Application/Telegram workflow decomposition | `TASK-P04-001..014` |
| F5 | Architecture reliability and convergence | `TASK-P04-015..017` |
| F6 | Functional/NFR reconnection and acceptance | `TASK-P05-001..017` |
| F7 | Operations and production-readiness evidence | `TASK-P06-001..011` |

## Gate rule

A phase closes only when its owned tasks have the evidence required by
`005-tasks`, relevant quality/security gates have been rerun, and any
environment-gated evidence is explicitly recorded rather than assumed.

F4 and F5 deliberately split PLAN-004: F4 performs workflow-by-workflow
migration; F5 verifies reliability, maintainability, reversibility and the
PLAN-004 exit gate after the migration is complete.

## PLAN-004 review/push subphases

Within the existing F4/F5 grouping, PLAN-004 uses four smaller non-normative
execution boundaries for review and push cadence. They do not alter frozen task
dependencies, owners or gates:

| Subphase | Approved task range | Purpose |
|---|---|---|
| A | `TASK-P04-001` | application workflow/admission seam |
| B | `TASK-P04-002..003` | execution/queue/recovery plus history |
| C | `TASK-P04-004..013` | derived data, search, summary and operations |
| D | `TASK-P04-014..017` | thin Telegram, reliability, convergence and exit gate |

Subphase A is published and closed (`a68ba1c`, with post-push regression repair `8beea3d`). Subphase B is published and closed: `TASK-P04-002` at `d805525`, `TASK-P04-003` at `bb7ccd9`, with publication closure at `b9f2eba`. Subphase C (`TASK-P04-004..013`) is verified/closed at functional revision `0e2bb0a`; this documentation commit is its publication boundary. Subphase D (`TASK-P04-014..017`) is next.

## Post-PLAN-004 tracking decision

The existing phase table and PLAN-004 Subphases A–D remain valid. No task owner,
dependency or plan gate is changed.

After `TASK-P04-017` closes PLAN-004, day-to-day progress reporting stops adding new
phase/subphase layers and uses the five outcome-based execution packages documented
in `POST-PLAN-004-EXECUTION-ROADMAP.md`. Frozen PLAN-005/PLAN-006 tasks remain the
authoritative checklist underneath that simplified view.
