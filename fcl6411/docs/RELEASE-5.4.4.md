# 5.4.4 — Signal Camera + Service-Safe Media

Signal 1.4.0 adds a browser camera attachment edge. On iPhone, **CAM** invokes the native rear-camera/photo capture UI; the captured image becomes a normal LO resource and can be followed by any prompt, including `what am I looking at?`.

## Data path

```text
Signal browser camera
  → Signal HTTP attachment
  → temporary local image path
  → LO resource selection
  → Fabric vision requirement
  → artifact staging / content identity
  → same-node or remote vision worker
```

The browser-to-Signal edge may carry image bytes, but the Fabric ingress rule does not change: image payloads are staged as artifacts before inference packets are dispatched. The existing work-packet size limit remains intact.

## Media reliability

Signal runs as a background service and therefore cannot assume an interactive shell PATH. LOOK now discovers mpv through explicit configuration, PATH, Linuxbrew, Homebrew, and common system locations. Signal's Linux service also receives a conservative PATH. Playback errors preserve the concrete edge diagnostic in the LO tool receipt.

## Interface contract

Camera capture is not a special `what am I looking at?` command. It is a generic image attachment control. This keeps Signal thin and lets the same LO/Fabric vision machinery handle screenshots, camera photos, dropped images, and future attachment sources.
