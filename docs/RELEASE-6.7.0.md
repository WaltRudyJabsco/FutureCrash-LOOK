# 6.7.0 · BEACON

BEACON starts the next transport stage without pretending Tailscale is already gone.

Fabric now has an optional public **rendezvous** plane for already-paired nodes. Each
pair derives an opaque 256-bit rendezvous slot from the authorization token it already
shares; the token itself never leaves either machine. A node's short-lived presence is
signed with its existing Ed25519 Fabric identity before a rendezvous service will accept
it. The service cannot create trust, run actions, read Fabric traffic, or decrypt Tailcat.

`lk fabric rendezvous set https://…` enables a rendezvous service. The resident node then
announces and resolves presence in the background. A successfully resolved peer adds
short-lived Tailcat address candidates while preserving the Tailcat certificate pinned
during pairing. Expired candidates disappear automatically.

A tiny self-hostable service ships as `fcl-rendezvous serve --host … --port …`. It keeps
presence only in memory: clients republish every few seconds, so restart means forgetting
presence rather than retaining user history.

This release deliberately stops at **secure rendezvous**. It does not yet implement UDP
hole punching or encrypted relay. Tailcat remains preferred when a direct candidate is
reachable; Tailscale remains the fallback while those next two networking pieces are
built.
