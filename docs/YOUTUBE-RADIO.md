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

## Signal and Albert

Paste a link and an instruction in the same message to add directly, for example:

```text
https://youtu.be/VIDEO_ID add this to YouTube Radio
```

“Please add LINK to YouTube Radio” and “save this to YTR LINK” also work.
Signal and Albert confirm the queue owner and item after the owner acknowledges
it. Repeated links are deduplicated. This prepares audio for later listening; it
does not open a player or start playback. The destination is the browser's
selected YTR owner, falling back to the host's CLI preference. Missing or multiple
links prompt for one link in the same message; failed requests are not reported
as successful additions.

Type **`/ytr`** in either chat to open the browser player, or visit `/ytr` on
that same host. `/ytr https://youtu.be/VIDEO_ID` opens the player with the link
prefilled; press **Add to queue** to submit it. A link remains in the chat if
popup blocking prevents the new tab from opening.

The browser defaults to the host's existing `lk ytr --node` preference. The
**Queue owner** selector lists paired nodes; choose the same owner as your
terminal to share its queue and bookmarks. This browser remembers your choice
without changing the host's CLI preference. Playback happens on the browser's
device; preparation and queue storage remain on the owner.

The responsive player includes a compact tape-reel animation, native seek bar,
play/pause, next, playback speed, position/total and remaining time. Queue rows
show duration and saved position, with add, reorder, remove and retry controls.
Finished audio advances to the next ready item. Mobile browsers may require a
Play gesture and may suspend background playback according to their own rules.

Positions synchronize while listening and when pausing
or leaving the page in the background. Unsynchronized positions are
retained in browser storage; on return, choose **Use saved position** or **Keep
this device’s position**. Concurrent edits use the same revision checks as the
CLI and cannot silently overwrite a newer bookmark. Browser storage must be
available to retain unsynchronized positions. Unlike the terminal cache, this
first web player needs its host and queue owner reachable for audio streaming.

The page and its `/api/ytr` gateway use the host's existing endpoint authorization.
Audio byte ranges pass through paired-node routing so seeking does not require
retransmitting the entire recording. Opening the player does not start a download
or playback automatically.

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
- **W** (Shift+W): open a sibling shell pane using the standard LOOK terminal controls.
- **Q**: save position and close this player.

Queue rows show saved position / total duration, with the current item updating live.
Playback also shows a progress bar and remaining time. Unknown durations display
an em dash until download metadata or the audio player provides a total. Existing
downloads recover duration from their retained metadata without downloading again.

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
