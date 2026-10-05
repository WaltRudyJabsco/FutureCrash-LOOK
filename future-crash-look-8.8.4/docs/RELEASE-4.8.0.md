# Future Crash + LOOK 4.8.0 — Fabric Dashboard

This release turns the now-hardened Fabric control plane into a visible operational cockpit.

## New

- `lk dash` — live terminal dashboard over resident Fabric APIs.
- `lk fabric dashboard` and `lk fabric dash` aliases.
- Node/model activity, trust basis, jobs, HTTP pressure, services, warnings, and recent events in one view.
- Dashboard shortcuts: `w` Fabric watch, `s` settings, `d` doctor, `r` confirmed managed-service restart, `q` quit.

## Design

The dashboard owns no configuration and duplicates no scheduler state. It polls the same `/v1/*` interfaces already used by LOOK and Fabric tools, at bounded cadences so observation does not become load.

Mutation remains explicit. The dashboard is read-only by default; service restart is restricted to Fabric-managed named services and requires confirmation.

## Reliability baseline

4.8.0 retains the 4.7.4 socket-ownership fix that eliminated the 7332 CLOSE-WAIT/backlog failure reproduced on the 3090.
