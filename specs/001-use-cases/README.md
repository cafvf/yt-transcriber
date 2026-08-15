# 001 — Current-System Use-Case Model

Version: **1.0.1**
Status: **Approved / Frozen**
Derived from: **000-baseline v1.0.1**
Reference date: **2026-08-15**

## Purpose

This package is the frozen behavioral bridge between the approved baseline specifications and requirement derivation. It models four different kinds of behavior without mixing them:

1. **Use cases (`UC-*`)** — goals intentionally initiated by the Authorized Operator through the product interface.
2. **System scenarios (`SS-*`)** — automatic runtime behavior required to preserve system invariants.
3. **Operational scenarios (`OS-*`)** — host/service procedures performed by the operator outside ordinary product interaction.
4. **Interface conformance (`IC-*`)** — consistency obligations for commands, aliases, help text, documentation, and handler registration.

A frozen use case describes actor goal, observable behavior, alternatives, postconditions, and relevant security constraints. It does not prescribe classes, modules, ports, test libraries, migration scripts, or implementation tasks.

## Frozen catalog

### Operator use cases

| ID | Goal | Main interface mapping |
|---|---|---|
| UC-001 | Transcribe or explicitly reprocess supported media | URL, Telegram audio/voice/document, `/transcribe`, `/pt`, `/en`, `/redo` |
| UC-002 | Monitor current processing and queue | `/status`, `/queue`, `/fila` |
| UC-003 | Cancel active and/or pending work | `/cancel`, `/clearqueue`, `/cancelall` and aliases |
| UC-004 | Browse and retrieve completed history | `/list`, `/last [n]` |
| UC-005 | Search completed history | `/search <texto>` |
| UC-006 | Rename or merge speaker labels | `/rename [n]` + interaction |
| UC-007 | Generate a summary | `/summary [n]` |
| UC-008 | Export a transcript | `/text`, `/export`, `/json`, `/srt`, `/vtt` |
| UC-009 | Generate YouTube MP4 with selectable subtitles | `/video_subs`, `/videosubs` |
| UC-010 | Inspect runtime health | `/healthcheck` |
| UC-011 | Inspect the latest operational error | `/lasterror` |
| UC-012 | Clear reconstructible cache/model data | `/clearcache` |

### System scenarios

| ID | Goal | Trigger |
|---|---|---|
| SS-001 | Reconcile persisted Jobs after restart | process startup |
| SS-002 | Apply retention to volatile artifacts | retention trigger after normal operation |

### Operational scenarios

| ID | Goal |
|---|---|
| OS-001 | Exercise and operate the systemd service lifecycle |
| OS-002 | Back up and restore private durable state |
| OS-003 | Upgrade and roll back the deployment safely |
| OS-004 | Recover preserved artifacts manually after delivery failure |

### Interface conformance

| ID | Goal |
|---|---|
| IC-001 | Keep registered commands, aliases, help text, and current/future documentation consistent |

## Freeze rule

Version 1.0.0 is frozen for requirement derivation. A later correction that changes the meaning, actor goal, success outcome, or scope of a frozen item requires an explicit versioned amendment. Editorial clarifications that do not change semantics may be patch-version changes.

New product functionality must not be smuggled into this package while deriving requirements. It belongs to a later feature specification after the Architecture & Specification Baseline milestone is closed.
