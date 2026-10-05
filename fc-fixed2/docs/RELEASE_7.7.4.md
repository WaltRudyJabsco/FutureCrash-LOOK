# 7.7.4 — CLEAN START

Installer and native-preview hardening over 7.7.3 PREVIEW BRIDGE.

- macOS Unified Node installation now requires launchctl bootstrap and explicitly kickstarts the node before live-version verification.
- Failed macOS node verification reports launchd state, the node log, and the :7332 owner instead of Linux systemctl instructions.
- Failure rollback kickstarts the restored macOS node after bootstrap.
- Linux terminal provisioning checks Kitty, ImageMagick, and Poppler independently, so preinstalled Kitty no longer suppresses preview-helper installation.
- Kitty can display PNG files directly even without ImageMagick; converted formats retain the bounded thumbnail cache.
- Kitty placements use C=1 so graphics painting cannot move LOOK's text cursor.
- Installer prompt convention remains standard: [Y/n] means Return=yes; [y/N] means Return=no.
