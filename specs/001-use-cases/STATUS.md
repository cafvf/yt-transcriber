# Use-Case Stage Status

Package: **001-use-cases**
Version: **1.0.1**
Status: **Approved / Frozen — Review Gate Passed**
Derived from: **000-baseline v1.0.1**
Reference date: **2026-08-15**

## Review result

The reorganized model passed a second review using the same criteria applied to the initial draft:

- each `UC-*` represents an intentional operator goal rather than a handler name or internal mechanism;
- goals are at comparable abstraction level;
- syntactic aliases are mappings, not duplicate use cases;
- `/redo` is an alternative entry to UC-001 because the current baseline only creates a new Job and re-enters the normal transcription flow;
- startup recovery and retention are automatic system scenarios, not human use cases;
- systemd, backup/restore, rollback, and manual recovery are operational scenarios, not product use cases;
- `/start` and `/help` are interface-conformance behavior rather than a distinct business goal;
- no future feature (semantic search, translation, alternative ASR, advanced redo, Obsidian/Notion) was introduced;
- canonical transcript, Job lifecycle, privacy, and security semantics remain consistent with `000-baseline v1.0.1`;
- each item has a clear path to requirement families without forcing implementation detail.

## Changes from 0.1.0-draft

- UC-010 `Reprocess` merged into UC-001 as explicit reprocessing flow.
- Former UC-011..013 renumbered to UC-010..012.
- Former UC-014 and UC-015 moved to SS-001 and SS-002.
- Former UC-016 moved to IC-001.
- Added OS-001..OS-004 for currently required private-production operational behavior/evidence.

## Patch clarification in v1.0.1

UC-004 now states explicitly that history indexes are deterministic positional indexes over the current completed-history ordering, not durable identifiers. This matches the current implementation, which recomputes completed history for each selection. The clarification does not change the actor goal or product behavior.

## Gate decision

**PASS.** `001-use-cases v1.0.1` is frozen and may be used as normative behavioral input for `002-requirements`.
