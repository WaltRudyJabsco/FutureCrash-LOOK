# Future Crash + LOOK 8.7.2 — FOREGROUND CAPTURE

Local Fabric Vision capture belongs to the foreground command that the user explicitly invoked. `lk vision screen` and local watch sessions call the shared `fabric_vision.capture_screen()` module directly. A real remote target such as `lk vision screen @m4` still routes through Unified Node and authenticated Fabric transport.

This distinction matters on macOS, where Screen Recording authorization is process-responsible, and on Linux, where Wayland/X11 session environment belongs to the interactive desktop process.
