# 7.7.8 — MEDIA IDENTITY

- Fix MM/MN/MP system-owner dispatch signature and execute the transport path in regression tests.
- A remote media URL carries node, catalog ID, and catalog path locator. ID remains canonical; path recovery is permitted only when the path is present in the remote node's current media catalog.
- Preserve Range streaming, native previews, and the 7.7.7 player ownership rules unchanged.
