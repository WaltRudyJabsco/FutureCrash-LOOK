# Future Crash + LOOK 8.7.0 — FABRIC VISION

Fabric Vision makes trusted nodes visually observable on explicit request without creating an always-on screenshot service. `lk vision screen` captures once, `@NODE` routes through authenticated Fabric transport, `--ask` feeds the ephemeral frame directly to the selected local vision model, and `--save` is the explicit persistence boundary.

`--watch` is a requester-owned foreground loop capped at ten minutes with a minimum two-second interval. Endpoints capture only when polled, keep no screenshot history, and omit image bytes when the current frame hash matches the requester's previous hash.

See `docs/FABRIC-VISION.md` for the transport and privacy contract.
