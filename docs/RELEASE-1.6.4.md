# Future Crash + LOOK 1.6.4

Signal CRT release.

## Changed

Signal now behaves like a tiny persistent display device rather than a temporary drawing panel. Model output defines framebuffer/animation state; Future Crash owns continuous scan and frame timing. Signal requests are recognized directly (`signal`, `animated`, `sprite`, `EQ`, `dashboard`, etc.), and animation requests explicitly require `FPS` plus multiple `FRAME` sections instead of prose-only discussion. `TTL` remains available for intentionally temporary displays.
