# Future Crash + LOOK 2.9.0

This release makes LO file actions safer and more inspectable.

`search_files` now means path/name discovery only. `search_content` is a separate text-only operation delegated to ripgrep. Requested media playback can use VLC, and every LO filesystem action writes a compact bounded audit receipt.

The agent loop also gains a repeated-call guard and bounded task trace, establishing the internal seam for a later continuation/checkpoint engine without coupling that work to the terminal UI.
