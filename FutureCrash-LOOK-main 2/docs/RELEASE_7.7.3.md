# Future Crash + LOOK 7.7.3 — PREVIEW BRIDGE

- Reuses the proven ASCII-first native preview adapter in the ordinary wide list side pane.
- Adds Kitty graphics protocol support for Linux; unsupported terminals remain ASCII-only.
- Linux PDF thumbnails use `pdftoppm` when available; image thumbnails use ImageMagick when available.
- Fixes macOS Albert installation by explicitly kickstarting the bootstrapped LaunchAgent and surfacing launchd state on failure.
- Kitty remains an optional recommended terminal in the installer; failure to install optional terminal components never changes LOOK's ASCII fallback contract.
