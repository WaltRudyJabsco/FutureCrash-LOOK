# Taking a Fabric computer offline

The catalog remembers media on sleeping or disconnected computers. Remembering
an item does not mean its bytes can play here. MP, TV and Media Find check only
visible rows in the background: **local** means an existing local file,
**remote** means a source answered a recent check, **checking** means unverified,
and **offline** means no copy answered. Offline rows are muted but remain
selectable for management. Checks expire after ten seconds; playback verifies
its chosen physical copy again. Streams keep their own streaming behavior. A player opening a source reports
**loading**, with unknown times shown as `--:--`, until its decoder and media clock
are ready. Source startup has a twelve-second budget; a stalled source does not
receive a successful playing receipt.

Before leaving, mark items in **lk mp**, **lk tv** or **lk media find**, then press
**Shift-Y — keep offline**. Choose this computer's library or a mounted travel
drive, review the count, catalog size and destination, then confirm. Copies show
progress, check free space and length, compare the catalog SHA-256 when present,
and re-read the saved data before publishing it. Audio/video files are unchanged.
An interrupted copy is removed; completed copies remain. Existing different
files are never overwritten. Copying a protected file does not grant playback
rights; it still needs its authorized provider app.

From a terminal:

```sh
lk media offline "artist or movie title"
lk media offline --queue
```

The second form retains the current queue's items. Saved copies are indexed
locally and added to matching queue locations. Unmounting a travel drive makes
its files unavailable until reconnected. There is no automatic eviction, sync,
or deletion of originals. Remove unwanted copies using the normal file browser.

Inference excludes peers whose advertisements have failed or expired, then
checks a remote connection with a short budget before spending time starting a
model. A failed transport can fall back to another capable worker, including
this computer. Explicit model/capability requirements are preserved. When the
local Fabric service is unavailable, an installed local Ollama-compatible runtime
can provide a fallback; a model still must advertise the required capabilities.
No models are downloaded automatically and no network setting is changed.

In Future Crash, **Ctrl-C** cancels running and queued Oracle requests. The next
request gets a fresh cancellation token; late replies cannot replace it. Escape
retains its existing return/detach behavior. Clients also request cancellation of
unfinished Fabric jobs when polling expires or a stream is closed; an unreachable
worker cannot acknowledge cancellation until reachable again.

Two new ambient visualizers, **Aurora Loom** and **Paper Lanterns**, are included
in the ten-second Cycle. They pause with playback and use terminal foreground
colors so Paper, Slate and Neon retain their own palettes.
