# Frozen Current-System Behavioral Model

Version: **1.0.0**
Status: **Approved / Frozen**

## 1. Actor and system boundary

The primary human actor is the **Authorized Operator** configured for the private Telegram bot. Supporting external actors/mechanisms include Telegram Bot API, YouTube/yt-dlp, ffmpeg/ffprobe, ASR/diarization backends, optional OpenAI-compatible text generation, SQLite/filesystem implementations, and the host/systemd runtime.

Supporting mechanisms do not own business policy. Credentials used by them remain infrastructure/composition concerns.

## 2. Behavioral dependency model

```text
UC-001 Transcribe / explicitly reprocess media
  ├─> UC-002 Monitor processing            [optional observation]
  ├─> UC-003 Cancel work                   [optional interruption]
  └─> produces completed canonical transcript evidence
          ├─> UC-004 Browse/retrieve history
          ├─> UC-005 Search history
          ├─> UC-006 Rename/merge speakers
          ├─> UC-007 Generate summary
          ├─> UC-008 Export transcript
          └─> UC-009 Generate subtitled YouTube video [YouTube only]

UC-010 Inspect runtime health
UC-011 Inspect latest operational error
UC-012 Clear reconstructible cache

SYSTEM SCENARIOS
SS-001 Startup/restart reconciliation
SS-002 Retention of volatile artifacts

OPERATIONAL SCENARIOS
OS-001 Service lifecycle/systemd
OS-002 Backup and restore
OS-003 Upgrade and rollback
OS-004 Manual artifact recovery

INTERFACE CONFORMANCE
IC-001 Commands / aliases / help / documentation / handler consistency
```

## 3. Core dependency interpretation

UC-001 establishes source identity, durable Job state, processing provenance, canonical structured transcript evidence, canonical Markdown rendering, and delivery outcome. UC-002/003 depend on the Job/queue model. UC-004..009 depend on persisted completed evidence; UC-009 additionally depends on YouTube source identity/media reacquisition.

SS-001 and SS-002 preserve lifecycle/data invariants automatically. OS-001..004 are operator procedures required for private-production confidence but are not ordinary Telegram product goals. IC-001 keeps the public interaction surface truthful.
