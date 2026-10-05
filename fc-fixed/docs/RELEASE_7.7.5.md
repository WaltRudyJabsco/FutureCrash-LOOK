# 7.7.5 — TRUE FRAME

A hardening release for native preview geometry and macOS Fabric ingress startup.

- iTerm2 and Kitty native previews preserve source aspect ratio, contain within LOOK's existing preview rectangle, and center in the unused space.
- ASCII/Chafa still renders first and remains the fallback.
- macOS Fabric ingress is now explicitly bootstrapped and kickstarted under launchd before :7333 readiness is accepted.
- Failed ingress readiness reports launchd/systemd state, recent ingress log, and the :7333 port owner.
