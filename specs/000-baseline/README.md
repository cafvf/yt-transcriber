# 000 — Architecture & Specification Baseline

Version: **1.0.0**
Status: **Approved**
Constitution: **v1.0.0 (Ratified)**

## Goal

Reconstruct and ratify the current system contract, then eliminate known architectural and methodological inconsistencies before any new product functionality is implemented.

## Scope

This package is pre-REQ and contains product, architecture, domain, data/artifact, quality, security/operations specifications plus the decision ledger and deferred decision register.

It intentionally does **not** contain detailed use cases, atomic requirements, implementation plans, or task breakdowns.

## Current state

The specification package was explicitly approved on 2026-08-15 and is normative as **v1.0.0**.

The executable baseline validated on 2026-08-15 is green for the default local gate, while known architecture/taxonomy debt remains. Approval of the specification does not claim that those deviations are already corrected; it defines the target contract against which the correction milestone will be derived.

## Next-stage direction

With this package approved:

1. describe current use cases from the approved baseline;
2. derive the system requirement tree;
3. derive atomic requirements with acceptance criteria;
4. resolve requirement-derivation decisions (`RD-*`) as they become concrete;
5. build dependency-aware implementation plans/tasks and resolve planning decisions (`PD-*`);
6. execute corrections under TDD;
7. close verification decisions (`VD-*`) with automated and operational evidence;
8. only then reopen feature development.
