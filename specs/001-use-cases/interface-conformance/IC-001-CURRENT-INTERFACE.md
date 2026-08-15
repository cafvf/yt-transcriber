# IC-001 — Current interaction surface conformance

Version: **1.0.0**
Status: **Approved / Frozen**

## Purpose

Keep the current operator interaction surface truthful and internally consistent without treating help/discovery as a separate business use case.

## Conformance obligations

- Registered primary commands and aliases match help text and operator documentation.
- Current commands are not documented as future.
- Future commands/features are not advertised as available.
- `/start` and `/help` expose no secrets/private history.
- Command aliases map to the same underlying operator goal/behavior as their primary command.
- Documentation consistency tests are evidence, not authority over the approved specifications.
