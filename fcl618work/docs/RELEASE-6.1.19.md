# Future Crash + LOOK 6.1.19 — No Fixed Address

This release makes content identity independent of physical location.

- Small documents already opened for content indexing receive SHA-256 object identity.
- Fabric file search groups identical hashes into one logical object while preserving every physical node/path in `locations`.
- No files are deleted, moved, or deduplicated on disk.
- Large files remain cheap discoveries until explicitly promoted to content identity.
- Identified media streams through the generic range-capable Fabric artifact transport.
- Signal Window 1.9.0 presents video locally in the originating browser endpoint; audio and video share the same queue/output model.
- Unidentified media retains the existing source-node catalog stream, so playback never waits for a whole-movie hash.

Mental model: objects have identity; nodes provide locations; endpoints provide presentation.
