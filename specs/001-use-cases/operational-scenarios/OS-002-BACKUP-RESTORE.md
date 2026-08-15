# OS-002 — Backup and restore

Version: **1.0.0**
Status: **Approved / Frozen**

## Goal

Create and restore a protected backup of durable private state without corrupting the running service or exposing sensitive information.

## Scenario

Quiesce/stop as required, create protected backup, restore into a controlled installation/staging environment, validate SQLite readability and post-start `/healthcheck`, `/status`, `/list`, and record restart reconciliation behavior. Backup contents and evidence remain sensitive.
