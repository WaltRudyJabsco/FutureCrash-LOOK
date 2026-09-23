# 6.1.2 — Fabric Endpoint Route Repair

This is a surgical repair to 6.1.1. The endpoint approval and revocation handlers existed, but were placed in the Unified Node GET dispatcher while the CLI correctly sent POST requests. The result was an unconditional HTTP 404 even on the Signal host.

The four mutation routes now live in `do_POST`: `/v1/endpoints/fabric/allow`, `/v1/endpoints/fabric/revoke`, `/v1/endpoints/allow`, and `/v1/endpoints/revoke`. Read-only endpoint listing remains in `do_GET`. Fabric-wide approval and the CLI migration fallback are unchanged.
