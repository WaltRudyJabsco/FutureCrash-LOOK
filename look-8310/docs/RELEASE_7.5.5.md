# 7.5.5 — INSTALLED TRUTH

A surgical installer hardening release.

- Ships `core/attention.py`, required by the 7.5.4 attention router.
- Adds an installed-layout regression that constructs a clean HOME from the installer's own file manifest and executes `fcl-node --version-number`.
- Installer version verification now preserves and prints startup/import errors instead of reducing them to `unavailable`.
- No navigation, Albert, voice-policy, or attention-routing behavior changes.
