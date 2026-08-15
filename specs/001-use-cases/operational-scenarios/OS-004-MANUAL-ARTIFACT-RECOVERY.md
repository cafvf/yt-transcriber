# OS-004 — Manual artifact recovery after delivery failure

Version: **1.0.0**
Status: **Approved / Frozen**

## Goal

Recover preserved local artifacts after a controlled `delivery_failed` condition without reopening the terminal Job or exposing private data publicly.

## Scenario

Produce or identify a controlled `delivery_failed`, use `/lasterror` to obtain sanitized context, verify local artifact existence, recover/copy the artifact manually using the private runbook, and record evidence. Automatic re-delivery is not part of this baseline.
