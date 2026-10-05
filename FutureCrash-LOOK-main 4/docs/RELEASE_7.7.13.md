# 7.7.13 — CATALOG TRANSPORT

Fix remote `lk media find` playback without changing the working Classics/Arts playback path.

A remote catalog row may carry both a catalog `id` and a SHA-256 `digest`. The digest is an identity checksum, not proof that the bytes are registered in Fabric's artifact store. LOOK now routes catalog rows by `node + id` through `/v1/media/item`; `/v1/media/artifact` remains the fallback for artifact-only queue entries with no catalog locator.

Regression coverage locks that precedence so identified catalog media cannot silently become artifact transport again.
