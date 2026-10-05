# Future Crash + LOOK 7.7.18 — Albert Native Audio

Albert catalog playback now keeps Fabric audio on the browser native `<audio>` path.
The decorative EQ no longer inserts a Web Audio `MediaElementSource` into same-origin
Fabric playback. This removes the one playback-graph difference between working
Classics and failing Fabric tracks on Safari/WebKit while preserving the ticketed,
range-capable media source added in 7.7.17.

No changes were made to Signal media, LOOK/mpv, Fabric `/v1/media/item`, MM/MN/MP,
All Classical, or Classic Arts.
