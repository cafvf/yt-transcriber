# UC-009 — Generate YouTube MP4 with selectable subtitles

Version: **1.0.0**
Status: **Approved / Frozen**
Derived from: **000-baseline v1.0.0**
Reference date: **2026-08-15**

## Goal

Produce a derived MP4 for a completed YouTube transcript with a selectable subtitle track.

## Primary actor

Authorized Operator

## Trigger

`/video_subs [n]` or `/videosubs [n]`.

## Preconditions

- Operator is authorized.
- Selected completed Job originated from YouTube.
- Canonical transcript evidence exists.
- Export limits are satisfied.

## Main success scenario

1. YouTube Job and structured transcript evidence are selected.
2. Required subtitle representation is generated.
3. Corresponding YouTube video media is reacquired from source identity.
4. MP4 with selectable subtitle track is produced.
5. Video is delivered.

## Alternative and exception flows

- Telegram-audio Jobs are rejected.
- Duration/size limit violations are rejected.
- Download/ffmpeg/delivery failures are sanitized and do not alter canonical transcript.

## Postconditions

- Transcript is unchanged; MP4 is a disposable derived artifact.

## Security and privacy notes

- YouTube cookies remain secret/private authentication material; generated video is private operator-controlled content.

## Current evidence references

- `src/yt_transcriber_bot/infrastructure/exporting/video_subtitles_exporter.py`

## Requirement dimensions to derive

- YouTube-only precondition
- export limits
- subtitle derivative
- cookie/credential boundary
- derived retention
