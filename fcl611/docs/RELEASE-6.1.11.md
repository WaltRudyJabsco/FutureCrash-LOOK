# Future Crash + LOOK 6.1.11 — Endpoint-Local Media + Version Repair

Signal browser endpoints now default media playback to themselves. A Fabric node is selected only when the user explicitly chooses a remote OUT target; that choice is session-local rather than persisted across reloads. Browser playback may still use a Fabric node as the catalog/source for range-capable audio bytes, but source and output are no longer conflated.

Release metadata is synchronized across the product VERSION, LOOK VERSION, Unified Node, Tailcat, and Ingress components so Dash no longer reports the stale 6.1.8 core version after a newer install.
