# Future Crash + LOOK 8.7.1 — FABRIC VISION WAYLAND

8.7.1 fixes Linux desktop capture on Wayland. ImageMagick `import` and `scrot` are now restricted to X11 sessions; Wayland prefers native compositor capture tools and falls back to the XDG Desktop Screenshot portal through the user's session bus.

The privacy model is unchanged: capture is user initiated, one frame at a time, temporary by default, and watch mode exists only as a bounded foreground client loop.
