# UC-007 — Generate a summary

Version: **1.0.0**
Status: **Approved / Frozen**
Derived from: **000-baseline v1.0.0**
Reference date: **2026-08-15**

## Goal

Produce a derived Markdown summary from canonical transcript evidence without replacing or mutating the transcript.

## Primary actor

Authorized Operator

## Trigger

`/summary [n]`.

## Preconditions

- The operator is authorized.
- Completed transcript evidence exists.
- Summary backend is enabled and operational.

## Main success scenario

1. The completed transcript is selected and loaded from canonical structured evidence.
2. Summary policy prepares/chunks input.
3. Configured text generation produces intermediate/final output.
4. A derived summary is stored and delivered.
5. Related textual-search state is refreshed when applicable.

## Alternative and exception flows

- Disabled backend is reported unavailable.
- Timeout/model/token failures are sanitized and do not mutate canonical evidence.
- External endpoint use occurs only when explicitly configured.

## Postconditions

- Original transcript remains authoritative; summary is explicitly derived.

## Security and privacy notes

- Sending transcript text to an external endpoint crosses the local trust boundary; API keys stay in adapter/composition boundaries.

## Current evidence references

- `src/yt_transcriber_bot/infrastructure/summarization/transcript_summarizer.py`
- `src/yt_transcriber_bot/infrastructure/summarization/openai_compatible_client.py`

## Requirement dimensions to derive

- text-generation port
- application summary policy
- chunk/token/timeout semantics
- provenance
- external disclosure
