# Future Crash + LOOK 5.2.16 — Media Sessions + Library Queue

5.2.15 proved that large artifacts can stream through Fabric. 5.2.16 turns that proof into a small daily-use media surface without creating a media application or storage worldview.

## MediaSession is the primitive

LOOK now owns a persistent `look-media-session-v1` queue independently of mpv. The queue records ordered media entries, current position, shuffle-at-construction, repeat mode, and playback state. mpv remains a dumb playback edge: LOOK mirrors the canonical queue into an M3U8 runtime file and reconciles live playlist position back into MediaSession.

This keeps player replacement possible later. Queue meaning belongs to LOOK/Fabric; codecs and rendering do not.

## Fast library index

`lk media scan ROOT` recursively catalogs common audio/video files into `~/.local/share/look/media_library.json` without hashing or decoding media bytes. The fast scan derives lightweight artist/album/title/track metadata from filesystem structure and filenames, so a large library remains cheap to audit and re-scan.

No root is hard-coded. `/srv/media/music` is a useful deployment convention, not part of the architecture.

Commands:

```text
lk media scan /srv/media/music
lk media library
lk media find "talking heads"
lk media artists
lk media albums
lk media play "Remain in Light"
lk media play /srv/media/music/Talking\ Heads --shuffle
```

Exact album and artist queries resolve to ordered queues; exact title queries resolve tracks; broader text searches remain available through `lk media find`.

## Queue + playlists

```text
lk media queue
lk media save Driving
lk media load Driving
lk media playlists
lk media playlist save Sunday
lk media playlist load Sunday --shuffle
lk media clear
lk media repeat [off|all]
```

Saved playlists contain the canonical queue only, not mpv PID/socket/runtime state. This keeps them inspectable and repairable if a future storage audit moves physical files.

## Tiny player UI

`lk player` opens a small live terminal view over MediaSession with title/artist/album, progress, queue position, shuffle/repeat state, and direct controls:

```text
space  play/pause
←/→    seek ±10 seconds
p/n    previous/next
r      repeat off/all
x      stop playback
q      close player without stopping audio
```

The player is a view, not a second media implementation.

## Artifact transport remains explicit

Same-node queue playback may hand a local file directly to mpv rather than loop it through HTTP. Cross-node/content-addressed entries still resolve through Fabric artifact streams. `lk media stream PATH` remains the explicit proof path for forcing file-backed artifact registration plus byte-range streaming.

That separation is deliberate: Fabric owns identity/location/transport; the edge should still take the cheapest correct local path when the bytes and playback capability already share a node.
