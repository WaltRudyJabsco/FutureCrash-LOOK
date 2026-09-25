# Future Crash + LOOK 6.2.3 — Know Your Limits

This reliability release makes natural-language media selectors consistent across terminal LO and Signal, and teaches Fabric to distinguish discovery from presentation compatibility without pretending a filename proves codec or DRM status.

## Intent consistency

Both LO and Signal now use the same `resolved / clarify / no_match` contract. LOOK prompt glyphs copied from transcripts are presentation only and are removed before normalization. `play any movie`, `play a movie`, and related deterministic selectors therefore reach the same structured Fabric intent on every surface.

## Conservative playability

Media queue rows carry a cheap playability hint even when they came from an older catalog. `.m4p` has explicit protection evidence and is marked `protected_or_restricted`; common browser containers are only `browser_candidate`; less browser-friendly containers are `native_preferred`. Runtime playback remains authoritative.

Signal Window 1.10.3 refuses explicitly protected browser playback before calling `play()`. Browser decode/unsupported failures retain their real diagnosis and recommend the cheap fallback: choose another object or a native output.
