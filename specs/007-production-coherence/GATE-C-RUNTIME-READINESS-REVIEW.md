# PLAN-007 — Gate C2 Runtime Readiness Review

Status: historical C2 implementation evidence for **P07-012 + P07-013**. Gate C later closed PASS after cumulative C1+C2+C3 reproduction; see [`GATE-C-CLOSURE.md`](GATE-C-CLOSURE.md).

`pre-commit` moves out of production requirements and into the dev dependency group.
The runner rebuilds the wheel and inspects `Requires-Dist` to prove that
`pre-commit`, `pytest`, `ruff` and `mypy` are absent from production metadata.

The runtime keeps `yt-dlp[default]`; for PyPI installations this is the official
path that includes `yt-dlp-ejs`.

YouTube readiness is version-aware: Deno >= 2.3.0 or Node >= 22.0.0, with both
`yt_dlp` and `yt_dlp_ejs` importable. The downloader already enables both Deno
and Node in its `js_runtimes` option. The local health probe captures versions
for yt-dlp, Deno and Node and the Telegram healthcheck renders the evaluated state.

The current official yt-dlp EJS documentation was checked on 2026-08-22. The
The installed CLI `yt-transcriber-bot --preflight` and final source-checkout-independent
systemd/clean-install proof were subsequently delivered by P07-014 / C3. Final cumulative
closure is recorded in [`GATE-C-CLOSURE.md`](GATE-C-CLOSURE.md).
