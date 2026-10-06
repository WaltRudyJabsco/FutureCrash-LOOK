# Future Crash + LOOK 6.0.0 — Fabric Authorization

6.0.0 is the trust-boundary release. Fabric identity is no longer descriptive metadata: remotely reachable node APIs now require credentials minted by pairing. Public health/identity/advertisement and the one-use pairing route remain reachable so a new node can discover and join; the local loopback control plane remains local.

Node pairing is deliberately human-scale. `lk fabric pair-code` emits an eight-digit, five-minute, one-use code and a compact `lk fabric pair NODE CODE` command; the long `fcl://` invitation remains available for QR transport. Pairing stores a reciprocal high-entropy bearer credential, and failed code guessing is attempt-limited. Existing 5.9 trust records do not contain credentials, so machines should be re-paired once after upgrading.

Signal Window 1.8.0 introduces accountless endpoint authorization. An unknown Safari/browser receives a six-digit pending code and cannot call Signal APIs until a trusted local operator runs `lk fabric allow CODE once|trust`. Trusted endpoints persist, temporary endpoints expire, and `lk fabric revoke-endpoint` invalidates credentials. `lk fabric endpoint-code URL [once|trust]` creates a one-use invitation suitable for an iPhone camera QR scan when `qrencode` is present. Endpoint credentials are scoped and stored in HttpOnly cookies.

This release intentionally separates authorization from transport. Tailscale may still carry the packets, but it no longer decides who belongs to the Fabric. Tailcat can therefore replace transport later without changing node or browser identity.
