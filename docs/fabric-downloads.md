# Fabric downloads and searchable descriptions

Run the unified installer on the client and the chosen download node. It installs yt-dlp and ffmpeg and the download runtime on macOS and Linux. The canonical command is `lk ytd`; no new shell alias is required.

```sh
lk ytd 'https://www.youtube.com/watch?v=VIDEO_ID' --node 3090
lk ytd find 'ukulele chord voicings' --node 3090
lk ytd 'https://youtu.be/VIDEO_ID' --to '@3090:/run/media/jreno/2TB Storage/Downloads'
lk ytd jobs --node 3090
lk ytd status JOB_ID --node 3090 --wait
lk ytd cancel JOB_ID --node 3090
```

`find` returns five titles and exact URLs. In an interactive terminal, choose a number to download; in a pipeline it only lists results. `find --json` is read-only. LO also has video search, download, and job-status tools. Ask explicitly to download and name the destination node. A queued receipt is not a playback-ready file.

Downloads execute on the chosen node through the paired Fabric connection. The default directory is that node's `~/Downloads/LOOK`; `--to` accepts a literal local-to-that-node directory or `@node:/...` / `@node:~/...`. Quote paths with spaces. Each video and its source metadata occupy a job subdirectory. No media bytes pass through the requesting Mac.

Jobs persist progress, bytes, percent when the total is known, speed, ETA, and completion/error state. Ctrl-C detaches the terminal; the job continues. Use `--detach` to return immediately, or `--json` for a queued JSON receipt. Node restarts mark unconfirmed active jobs failed; they are not silently restarted. The worker publishes completed media after merging and cleans its staging fragments during normal completion/failure/cancellation. Interrupted node processes may leave hidden staging folders for manual review.

The format preference favors MP4 with H.264/AAC for browser compatibility when available; fallback formats can still require a native player. Private videos, authentication, service restrictions, and unavailable formats return the provider's error. This wrapper does not request browser cookies or bypass access restrictions.

## Optional holding area

```sh
lk ytd 'https://youtu.be/VIDEO_ID' --node 3090 --holding
lk ytd keep JOB_ID --node 3090
lk ytd keep JOB_ID --to '@3090:/run/media/jreno/2TB Storage/Video'
```

Only `--holding` enables expiration, 30 days after publication. Its default is `~/Downloads/LOOK-Holding` on the execution node. Keep clears expiration and moves the job into permanent storage. An hourly check while the node service is running deletes only the job's recorded unchanged files. Extra files, symlinks, or fingerprint changes retain the folder for review. Ordinary downloads and unrelated files do not expire.

## Catalog freshness

Successful downloads register immediately in the owning node's file and media catalogs, with title, channel, source URL, description, and tags. Live Fabric queries can then find them; an offline peer cannot discover the update until it reconnects. If registration fails, the video remains downloaded and `lk ytd index JOB_ID --node NODE` retries indexing.

The media watcher also checks existing scoped library roots every five minutes, using directory changes to discover additions and removals. It avoids decoding or hashing the library. Explicit whole-filesystem `/` roots are excluded from automatic traversal. Rewriting an existing file without changing its directory requires a manual `lk media scan ROOT`; use `lk scan ROOT` to refresh document content.

## Searchable descriptions

```sh
lk describe '/path/to/file.pdf' --text 'Dive records and equipment notes' --keywords 'diving,equipment'
lk find 'equipment notes'
```

Descriptions live in the SQLite catalog, not inside the original files. Download facts retain source provenance; supported small documents gain an extracted text excerpt and frequent keywords during scanning. Extraction uses no language model. The stored size/mtime fingerprint prevents changed cataloged files from matching stale descriptions after a rescan. Rename/replacement metadata is refreshed by scanning; descriptions are not portable embedded file tags yet.

Weather requests for tomorrow, a weekend, five/seven days, or next week now use location-local daily dates. Each forecast row shows its date, conditions, high/low, and precipitation probability. Next week begins next Monday.

## Destination discovery and Linux opening

LOOK's destination picker starts remote nodes at common places: Home, existing user/shared folders, mounted drives, and indexed media roots. Choose **Filesystem /** to explore everything, or press **Tab** to switch common/full views. Inside a remote directory, Tab returns to that node's common places. Going above the root still shows Fabric nodes.

Destination prompts support Tab completion for node-qualified paths, including spaces and remote `~/`. Previously chosen directories appear as recent places for that node; matching recent destinations complete without a network browse. Local completion also descends into directories after a trailing slash.

`lk find QUERY` searches the indexed local and reachable trusted Fabric nodes. Supported document text, filenames/paths, metadata, descriptions, tags, and download source facts are searchable. It shows partial coverage when nodes are unavailable and prefers a local copy of a logical result when one is cataloged. A remote-only result cannot accidentally open a different local file with the same path; Y copies its node-qualified address. Discovery does not fetch remote bytes or inspect every possible file format.

On Linux, the installer registers **LOOK mpv** in the desktop and fills missing or stale media associations. Existing working defaults such as VLC remain in place. LOOK opens audio/video directly in the configured player or installed mpv; desktop opening of other file types uses the normal system opener. Mac defaults are unchanged. This repairs application discovery; a particular file can still fail decoding and must be checked on its owning machine.

Normal `~/Downloads/LOOK` downloads remain permanent. Only explicit `--holding` gives a job a 30-day expiry. Keep clears expiry and moves it into permanent storage; moving files yourself also causes the holding cleanup to retain changed manifests for review.

## LOOK-owned folder repair and Mac media preferences

Every node's `~/Downloads/LOOK`, `~/Downloads/LOOK-Holding`, and `~/Pictures/LOOK` is included in the periodic discovery repair, without requiring a manual root scan. Custom download/output folders are registered when LOOK creates content there. Downloads still register immediately on completion; generated images now register immediately too. The watcher checks on startup and every five minutes. Hidden incomplete download staging folders are excluded. Other nodes discover the owning node's published catalog through live Fabric queries; an unavailable node remains unavailable.

Normal media and file rescans import a neighboring `BASENAME.info.json` for supported media. Moving an MP4 and its sidecar together therefore restores its title, channel, source URL, description, and tags in its new location. The video plays without the sidecar, but moving only that video still leaves the descriptive information behind. Original files and existing manually entered catalog descriptions are preserved.

LOOK's Mac browser and file cards now honor the configured video/audio preference, as do explicit open/preview actions. `lk apps video VLC` selects VLC; `lk apps video mpv` can use the Homebrew executable without requiring an mpv app bundle. `system` retains the ordinary Mac default. These changes do not alter Apple media authorization or infer DRM from an `.m4v` extension.
