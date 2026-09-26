# Future Crash + LOOK 6.1.0 — Tailcat Direct Transport

6.1.0 fixes the first Fabric Endpoint management seam and begins removing Tailscale from the data path.

## Fabric-wide endpoint management

Signal endpoint state remains local to the node serving that browser, but management is now Fabric-wide. `lk fabric endpoints` aggregates pending/trusted/temporary browser endpoints from reachable trusted nodes. `lk fabric allow CODE once|trust` locates the single node that owns that pending code and performs the approval there. `lk fabric revoke-endpoint ENDPOINT_ID` does the same for revocation.

This fixes the 6.0 behavior where approving an iPhone code on a Mac failed if Signal was actually hosted on the 3090.

## Tailcat phase 1

Each installation now creates a local Tailcat TLS identity (when `openssl` is available) and runs a guarded native Fabric listener on port `7443`. Pairing records the peer's Tailcat endpoints and certificate. Clients pin that exact certificate, carry the existing Fabric node authorization credential, and prefer Tailcat over Tailscale whenever the peer is directly reachable.

Existing 6.0 pairings do not require another pairing cycle: while Tailscale is still available, a trusted peer advertisement can refresh transport metadata only when its Fabric public identity matches an already-trusted node. On the next refresh, direct Tailcat becomes eligible.

Tailcat phase 1 intentionally does **not** implement NAT traversal, relay infrastructure, or browser exposure. Tailscale remains a fallback/bootstrapping transport, and Signal/iOS may continue to use it for remote reachability. The point of this release is narrower: node-to-node Fabric traffic no longer needs Tailscale when the machines can already reach one another directly.

Use `lk fabric transport` to inspect which route is active.
