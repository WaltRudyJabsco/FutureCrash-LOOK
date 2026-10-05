# Future Crash + LOOK 8.5.1 — REMOTE COVER

8.5.1 is a narrow bug-fix release on the 8.5 stabilization baseline.

Remote media playback already streamed bytes through Fabric, but artwork extraction was local-only. `/v1/media/cover` now lets the owning node extract/cache embedded or sidecar artwork and return only that small image to the listening endpoint. LOOK caches the image locally and hands it to the existing Media Find/Player renderer.

The cover request is bounded to 2 MB and two seconds on the client. Missing artwork uses only a short in-memory negative cache; no permanent miss marker is written.

No unified Media UI changes are included.
