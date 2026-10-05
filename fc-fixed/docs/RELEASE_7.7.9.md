# 7.7.9 — MEDIA IDENTITY

This release is based on the field-tested 7.7.8 MEDIA SESSION bundle. It changes only the Fabric media identity/stream boundary plus the tests that prove it.

- Signal and LOOK now consume the same canonical `/v1/media/audio` stream.
- Remote catalog playback carries the source node, catalog ID, and exact scanned path. The ID remains primary; the path is accepted only when it matches a row in the source node's current media catalog.
- Existing content digests use the artifact stream directly.
- Range requests and response metadata are forwarded end to end.
- The legacy `/v1/media/item` route remains for compatibility; new clients do not choose it.
- Media Session ownership and MM/MN/MP behavior are otherwise unchanged.
