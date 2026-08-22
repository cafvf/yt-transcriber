# PLAN-007 — Gate C1 Configuration Boundary Review

Status: implementation evidence for **P07-010 + P07-011**; Gate C remains OPEN.

## Runtime configuration source

C1 separates the application settings model from runtime source discovery.

The canonical production service policy remains:

- `EnvironmentFile=/etc/yt-transcriber-bot/env`;
- `UMask=0077`;
- host preflight requires restrictive group/other permissions and an allowed owner.

systemd reads the private file and injects values into the process environment. The
application does not need to open a root-owned production file itself.

`YT_TRANSCRIBER_ENV_FILE` remains an explicit operator override, including the
pre-existing behavior that a relative path is resolved against the operator's CWD.

A repository `.env` remains a development convenience only when the runtime module
itself executes from `<checkout>/src/yt_transcriber_bot/...`. An installed wheel does
not discover `.env` from arbitrary CWD and does not search parent directories for
`pyproject.toml`.

## Credential ownership

`ProviderCredentials` remains the single configuration declaration owner for Telegram,
Hugging Face, summary API and YouTube cookie credentials.

Adapter/backend constructor parameters such as `hf_token` are injection points, not
configuration declaration owners. C1 tests and its architecture auditor make that
distinction explicit.

Both `AppSettings` and `ProviderCredentials` receive the same explicit dotenv source
when one is selected, while real process environment values retain precedence.

## Application boundary

`application/config.py` no longer owns project-root discovery, dotenv path resolution,
or `pyproject.toml` filesystem reads. This resolves the final governed direct-I/O
hotspot inherited from Gate B without introducing a generic filesystem abstraction.

## Deliberately not closed by C1

C1 does not claim Gate C PASS. The following remain owned by later Gate C packages:

- P07-012 runtime/dev dependency separation;
- P07-013 deterministic yt-dlp/EJS + supported Deno/Node preflight;
- P07-014 installed CLI/preflight, systemd checkout independence, and final clean-install proof.

Gate C closure remains cumulative over Gate A + Gate B + all Gate C packages.
