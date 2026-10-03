# 5.4.6 — Endpoint Media Cleanup

Signal keeps the chat composer generic: playback output selection now appears only on the active media card. Node choices show concrete availability reasons, and the card adds an ephemeral **This Device** browser endpoint. On iPhone Safari this appears as **This iPhone** and streams the active queue item through the browser without pretending the phone is a full Fabric compute node.

Browser playback uses the same logical queue. Moving from a node to the browser starts HTML audio first, then stops the source player; moving back to a Fabric node adopts the source session at the browser's current queue index before playback continues there. The browser endpoint disappears with the browser session and does not advertise compute/storage capabilities.

Fabric nodes now expose range-capable media audio bytes for browser endpoints and report whether a real playback edge is available. Missing `mpv` is surfaced as the reason a node output is unavailable rather than appearing as an unexplained grey choice.

`mpv` is promoted from an optional prompt to a standard LOOK workstation dependency. Fresh installs and upgrades install it through Homebrew/Linuxbrew when absent, so Macs automatically become usable media outputs after upgrade.
