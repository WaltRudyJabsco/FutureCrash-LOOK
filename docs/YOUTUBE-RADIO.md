# YouTube Radio

`lk ytr` is an audio-only listen-later desk. Add a video link, let the owning
Fabric node prepare its audio, then listen in a small terminal pane.

```sh
lk ytr 'https://www.youtube.com/watch?v=VIDEO_ID'
lk ytr
lk ytr --node YOUR_NODE
lk ytr list
```

The first two commands use this computer by default. `--node` selects and remembers
a queue owner on this endpoint. Choose the same owner on your other computers to
use the same queue and listening positions. The owner remains authoritative;
this is not a separate editable copy of the queue on every device. Playback
always happens on the computer running the desk.

Adding a link starts a persistent audio-only download, not playback. `yt-dlp`
selects `bestaudio`; ffmpeg prepares M4A audio. It does not fetch the video stream
just to throw it away. The existing downloader's limits, failure receipts and
explicit retry behavior apply. A link with a playlist parameter adds only that
video; account login and playlist imports are not part of this version.
See [yt-dlp format selection](https://github.com/yt-dlp/yt-dlp#format-selection).

## The desk

- **A**: paste or drag in a video URL at the prompt.
- **↑/↓**, **Page Up/Down**, **Home/End**: browse the queue.
- **Enter**: play/resume the selected item; a finished item starts over.
- **Space**: pause/resume; **←/→**: seek ten seconds.
- **N**: next item; completion also advances automatically.
- **U/D**: move the selection up/down in queue order.
- **X**: remove; active downloads are cancelled when possible. Completed owner files remain.
- **R**: retry a failed download.
- **O**: open the original video in the system browser.
- **V**: toggle the shared Tape Echo animation.
- **C**: clean finished and removed local audio copies.
- **Q**: save position and close this player.

Downloads and remote transfers run outside the input/render loop. The desk
prepares the current and next audio copy on this endpoint. An item marked
**offline ready** is fully cached here; owner-side readiness alone does not
promise offline playback. Transfers use a temporary file and publish only after
completion, with a 1 GiB per-item limit. Prefetch failures can be retried by
playing the item explicitly. This desk has its own mpv audio session and does
not replace the LK Player queue.

## Offline use, bookmarks and cleanup

The owner stores queue metadata in
`~/.local/share/future-crash-look/radio/queue.json` and audio beneath its `audio/`
folder. Each listening endpoint stores its queue snapshot, bookmarks and audio
copies in `~/.local/share/look/radio/` under an owner-specific directory. The
owner choice is in `~/.config/look/radio.json`.

Offline, the last queue snapshot and completed local audio remain available.
Queue edits require the owner. Listening positions are saved locally and retried
with `lk ytr sync`; quitting also attempts synchronization. An older bookmark
cannot silently replace progress written by another device. To resolve a reported
conflict, inspect `lk ytr list`, then explicitly choose:

```sh
lk ytr resolve 2 --keep local
lk ytr resolve 2 --keep remote
```

`lk ytr clean` removes local copies of finished or removed items. Unfinished audio
is retained; owner files are retained even after removing a queue entry. There is
no automatic expiry, cloud account integration or guarantee that every YouTube
video is downloadable. A failed download remains visible for retry.

## One shared animation collection

**Tape Echo** and **Deep Space Relay** join the existing animation collection.
Both can be used by media playback, `lk saver`, and the desktop PIN curtain's
**V** control. They are ambient animations, not measurements of audio or network
activity. Existing per-interface enabled selections remain unchanged; enable new
animations in the relevant picker if an existing saved selection excludes them.

```sh
lk saver 'Tape Echo' --preview
lk saver 'Deep Space Relay' --preview
```
