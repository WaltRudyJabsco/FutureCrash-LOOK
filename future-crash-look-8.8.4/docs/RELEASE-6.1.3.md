# Future Crash + LOOK 6.1.3 — Tailcat Edge Repair

Repairs two edge cases exposed by live multi-device testing.

- Fabric-wide endpoint approval now retries another known peer transport when the preferred direct Tailcat connection fails mid-request.
- Remote browser media playback now carries Fabric peer authorization and pinned TLS context when fetching audio from another node.
- Tailcat/ingress now supports HEAD and treats `/v1/media/audio` as a streaming response instead of buffering a complete track.

This preserves Tailcat-first routing while making Tailscale a genuine per-request fallback during the transition.
