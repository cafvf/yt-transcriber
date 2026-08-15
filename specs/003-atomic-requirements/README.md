# 003 — Atomic Requirements

Version: **1.0.0**
Status: **Approved / Frozen**
Derived from: **002-requirements v1.0.0 (Approved / Frozen)**
Reference date: **2026-08-15**

## Purpose

Convert the approved 66-family requirement tree into testable current-baseline obligations that can be used as the normative input to implementation planning and TDD.

The approved package contains **66 atomic REQs**. The count happens to match the family count, but is not intentionally one-to-one: `DATA-TRANSCRIPT` + `DATA-MARKDOWN` remain one inseparable canonical-persistence obligation, while `FUNC-DIAG` and `NFR-RESOURCE` each require more than one atomic REQ.

## Approval basis

Before approval, all original 57 draft REQs and `DD-001..DD-007` were semantically reviewed for necessity, atomicity, testability, brownfield compatibility, constitutional consistency, hidden future scope and premature implementation detail.

That review:

- split 9 over-broad draft REQs into independent obligations;
- revised ambiguous/non-observable criteria;
- retained the frozen product scope;
- produced 66 final REQs with 66/66 family coverage and an acyclic dependency graph.

See `SEMANTIC-REVIEW.md`, `APPROVAL.md`, and `FREEZE.md`.

## Waves

- **A** — security, domain and data truth;
- **B** — architecture reconvergence;
- **C** — cross-cutting non-functional constraints;
- **D** — current functional contract reconnection;
- **E** — operational closure and evidence.

Waves describe conceptual dependency/review order. They are not forced commit batches.

## Normative use

Planning may now derive implementation plans from these REQs. Plans and tasks must preserve each REQ's acceptance criteria, direct dependencies, evidence requirements and scope guard.

No implementation plan may weaken an approved REQ merely to preserve a known brownfield defect. Conversely, a plan must not change frozen behavior unless an approved REQ or derivation decision explicitly identifies the current behavior as a defect, security hardening target, taxonomy correction or compatibility migration.

## Next stage

Create implementation plans from the approved atomic requirements, then derive tasks and TDD evidence. Product feature expansion remains frozen until the Architecture & Specification Baseline remediation is complete.
