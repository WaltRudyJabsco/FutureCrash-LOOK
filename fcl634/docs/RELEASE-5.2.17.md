# Future Crash + LOOK 5.2.17 — Fabric Media Catalog + LOOK Selector

5.2.17 keeps the media experiment deliberately small while using it to finish several general Fabric primitives: discovery across nodes, progressive content identity, duplicate-location merging, interactive selection, and catalog-backed completion.

## Search is selection now

`lk media find QUERY` no longer prints names that must be copied perfectly into a second command. In an interactive terminal it opens a LOOK-native selector:

```text
FABRIC MEDIA FIND
────────────────────────────────────────────────────────
›  Talking Heads — 04 Once in a Lifetime · Remain in Light   ◆ 3090
   Talking Heads — 05 Houses in Motion · Remain in Light     · 3090

↑↓ choose · Enter play · Space queue · A play matches · / filter · I info · Esc exit
```

The label is presentation only. Selection resolves directly to the catalog record/artifact identity. Non-interactive callers still receive plain text.

## One online catalog

Each Unified Node publishes its local cheap scan index at `/v1/media/catalog`. A Fabric node can expose the currently reachable union at `/v1/media/fabric`; `lk media fabric` summarizes it.

```bash
lk media fabric
lk media browse
lk media find miles
```

SHA-identical copies collapse into one logical row with multiple physical locations. A local copy is preferred when present. Rows without a digest remain separate because names and paths are not proof that bytes are identical.

## Progressive identity

`lk media scan` remains intentionally fast and does not hash every byte. Identity is upgraded only when useful:

```bash
lk media identify "Kind of Blue"
lk media identify /srv/media/music/Miles\ Davis
lk media identify --all
```

`--all` is intentionally node-local to avoid accidentally launching thousands of serial remote hashing requests. A specifically selected remote row can be identified on demand by its source node when Fabric needs to stream it.

Rescanning preserves an existing digest only when path, size, and mtime still match. A changed file loses the old digest and must be re-identified.

## Generic artifact registry

The Unified Node now also exposes `/v1/artifacts` and `/v1/artifacts/fabric`, making SHA-addressed artifacts discoverable independent of media. Media is one projection of the artifact system, not a special storage subsystem.

## Completion uses the same truth

Zsh media completion asks the online catalog for a bounded set of matching artists, albums, and titles. The command line, selector, and playback resolver therefore stop maintaining separate naming worlds.

## Deliberate stop line

This release does not add recommendations, ratings, lyrics, artwork animation, media-server transcoding policy, or a fixed `/srv/media` layout. mpv remains the decode/render edge; LOOK owns session/queue semantics; Fabric owns identity, location, discovery, and transport.
