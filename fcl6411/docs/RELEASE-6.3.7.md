# Future Crash + LOOK 6.3.7 — Window Seat

Native video now reliably opens a visible player when switching from an existing audio-only LOOK mpv session.

The key invariant is simple: audio/headless → video is a presentation-class change, so LOOK restarts only its own mpv worker with explicit video/window flags. Ordinary same-class playback still reuses the existing worker.
