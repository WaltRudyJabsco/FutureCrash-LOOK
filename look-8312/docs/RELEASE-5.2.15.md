# Future Crash + LOOK 5.2.15 — Streaming Artifacts + Media Proof

This release tests whether the Fabric artifact abstraction generalizes beyond AI. Large existing files may be registered in place, addressed by SHA-256, and consumed over HTTP byte-range streams without copying the whole file into Fabric state or memory.

The visible proof is intentionally small: `lk media add PATH`, `lk media play PATH`, and `lk media play @NODE sha256:DIGEST`. `mpv` is an optional playback engine and owns decoding/rendering; Fabric owns identity, location, peer routing, and byte transport. No media-library worldview or fixed storage root is introduced.

This keeps the upcoming 3090 disk/storage audit independent. Physical media locations can move and be re-registered while consumers continue to operate on artifact identity and stream capability.
