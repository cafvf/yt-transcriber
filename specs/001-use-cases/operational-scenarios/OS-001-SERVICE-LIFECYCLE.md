# OS-001 — Service lifecycle / systemd

Version: **1.0.0**
Status: **Approved / Frozen**

## Goal

Operate and validate start, status, stop, and restart of the private service on the real host/staging environment.

## Scenario

Exercise `systemctl` lifecycle actions, inspect `journalctl`, and verify post-start/restart responsiveness with `/healthcheck` and `/status`. Evidence must record environment, commit, commands, expected/observed results, and sanitized outputs.
