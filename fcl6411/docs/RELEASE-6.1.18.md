# 6.1.18 — Lights Out

Installer lifecycle repair only. The installer stops/unloads the managed Unified Node, installs files, starts it through the platform service manager, and verifies health. It no longer treats port 7332 as a pre-start ownership signal. If installation fails after retiring the node, the EXIT trap restores the managed node on Linux or macOS.
