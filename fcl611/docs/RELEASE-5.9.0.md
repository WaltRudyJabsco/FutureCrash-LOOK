# Future Crash + LOOK 5.9.0 — Fabric Identity

Every Fabric node now owns an accountless Ed25519 identity independent of Tailscale. The installer creates the keypair once, derives a stable node ID and fingerprint from the public key, and preserves the private key under `~/.config/future-crash-look/identity/`.

Use `lk fabric identity` to inspect the local identity, `lk fabric trust` to inspect trusted nodes, and `lk fabric pair-code` to open a five-minute one-use invitation. Pair with the emitted `fcl://pair` URI or endpoint plus short code. If `qrencode` exists, LOOK also renders the same invitation as a terminal QR code.

5.9.0 deliberately does not hard-enforce trust on all pre-existing Fabric API traffic yet. That keeps mixed installations working while identity propagates. Endpoint authorization and signed/scoped node requests are the next phase.
