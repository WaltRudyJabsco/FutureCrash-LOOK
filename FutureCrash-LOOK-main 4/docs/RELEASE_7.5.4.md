# 7.5.4 — ATTENTION ROUTER

A small hardening pass over 7.5.3. It fixes voice audition semantics and gives Fabric attention events a routing seam without pretending to know which device the user is currently using.

## Voice preview

- `lk voice preview` now auditions the configured **Default voice** directly.
- The `lk settings` Preview voice row displays that configured default rather than the currently resolved personality voice.
- Explicit `lk voice preview PROFILE` remains available.
- Personality voice resolution is unchanged for actual personality speech.

## Fabric attention

- Adds typed `fabric-attention-v1` events separate from speech transport.
- Adds `lk alert [@TARGET] MESSAGE` for explicit voice attention delivery.
- Targets supported now: origin/local node, a named Fabric node, a named authorized browser endpoint, and `@all`.
- `@active` and `@follow-me` are reserved policies but deliberately return `presence-unresolved` until Fabric has trustworthy ephemeral presence evidence. No device is guessed.
- Browser delivery reuses endpoint authorization, capability advertisement, queueing, and effect receipts; native-node delivery reuses canonical `audio.speak`.
- The schema already admits future sound, visual, and beacon delivery adapters without redefining the event.

## Albert field notes

Two observed issues are intentionally recorded rather than patched ad hoc in this release:

- PLACES/map results are still inconsistent in framing/usefulness and need an evidence-driven Albert pass.
- Natural media requests such as `play some clash` do not yet reliably reach the same canonical Fabric media path as the classic surfaces; Albert must consume the established media action/receipt pipeline rather than grow a parallel one.
