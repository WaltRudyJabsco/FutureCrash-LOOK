# 5.4.5 — Node-Scoped Media Outputs

Fabric media now models the queue/session separately from the playback endpoint. Each online node exposes a default media output and its own LOOK-owned session. Signal 1.5.0 adds an **OUT** selector, routes direct media requests and transport controls to that node, and can hand an active session to another node while preserving queue/current index.

The node control plane exposes local media state/output plus routed play/control and full-session handoff. LOOK adds `lk media outputs` and `lk media on NODE ...` for deterministic operator access. Remote queue items continue to resolve through Fabric artifact streaming and progressive SHA identity.

The iPhone camera composer also now uses real selected prompt text after capture: Return accepts `what am I looking at?`; typing replaces it.
