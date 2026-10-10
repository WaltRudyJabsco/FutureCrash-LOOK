# 8.15.0 — Correct media metadata together

Media Find, album track lists and LKMP offer E to edit the current or marked
tracks. Tab marks individual tracks, A selects all shown, and blank input keeps
existing values. Shared artist/album/disc fields apply across the selection;
individual title and track fields appear for a single track. R refreshes the
catalog view. The command-line equivalent is lk media edit QUERY with field flags
and --all for an explicit batch.

Owner-local .info.json corrections preserve audio/video bytes, unrelated source
metadata and individual song titles, survive rescans and flow through the fabric
catalog. Catalog IDs and expected metadata prevent stale or arbitrary-path edits.
Failures roll back an owner’s sidecars; cross-owner results report partial success.

Bundle/Albert 8.15.0; LOOK 4.62.0; Future Crash 1.3.0.

Validation: 1,045 automated tests passed, including A/E selection flow, bulk
field preservation, rescan persistence, owner routing, stale sidecar rejection
and rollback after failed catalog writes.
