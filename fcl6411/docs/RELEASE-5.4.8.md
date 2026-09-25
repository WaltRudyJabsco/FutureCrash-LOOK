# 5.4.8 — Media Output State Repair

Signal now has one authoritative media-output target. Browser endpoints are ephemeral per-tab targets; Fabric nodes are `node:<id>` targets. Polling can refresh state but cannot overwrite the selected output.

The iOS handoff transaction no longer destroys/recreates the native output selector inside its own change event. Safari first accepts browser audio, then the source node is stopped. Failure before playback restores the previous target; a source-stop failure after playback is reported as a warning.

Playback-node discovery now asks whether the node can accept a session (LOOK + mpv), rather than requiring an existing local session. This removes the false grey/unavailable state seen on newly upgraded Macs.
