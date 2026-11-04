# LOOK Museum

`lk museum` opens a terminal collection browser. `/museum` opens the same collection
through Signal or Albert, with a responsive web gallery and slideshow. Existing
arts-channel and `lk classics` commands are unchanged. This is the first museum
milestone, not a Gutenberg download pack or a replacement for Mercury Reader.

## Start a collection

```sh
lk museum
lk museum --node YOUR_COLLECTION_OWNER
lk museum search landscape --source met
lk museum search 'Japanese woodblock' --source aic
lk museum save aic-27992
lk museum starter --count 1000
lk museum status
lk museum cancel
```

A fresh installation starts on `local`; choosing `--node` remembers a paired
collection owner in `~/.config/look/museum.json`. To keep the main collection on a
home archive computer, select that computer explicitly. Nothing is downloaded
merely by opening the desk or gallery. Discovery is online; saved browsing and
local artwork remain available offline.

The **starter pack** uses twenty chosen subjects across landscapes, portraits,
Japanese prints, ancient Egypt, Chinese painting, Indian sculpture, Islamic
ceramics, Dutch painting, Impressionism, architecture, birds, oceans, textiles,
musical instruments, African sculpture, Greek vases, manuscripts, photography,
flowers and still lifes. It distributes selections across themes and sources,
rather than randomly sampling one large museum result set. Individual selections
come from museum search rankings; this is a themed starter, not a claim that each
work was individually curated by an art historian.

Choose 1–1000 works. Existing saved objects are reused. Requests are paced and
images are limited to 20 MiB each; the local collection has a 3 GiB budget. The job
runs on the selected node, reports actual saved counts and errors, and can be
cancelled. A node restart marks unfinished work **interrupted**; start again to
reuse completed downloads. Source failures or unavailable images can produce a
partial pack. Completion is never inferred from the requested count.

## Terminal controls

- Arrows, Page Up/Down, Home/End: select artwork.
- **Enter**: view a downloaded work; **I** switches native image/ASCII preview.
- **D**: discover online; **T** changes Met/Art Institute source.
- **/**: search the current collection or discovery view; **N/B** pages discovery.
- **L**: return to the saved collection; **R** refreshes status.
- **K**: keep the selected result offline on the owner.
- **P**: copy a saved owner artwork to this endpoint.
- **F**: toggle a saved work's favorite flag.
- **A**: choose a starter download size (Enter cancels).
- **W**: standard LOOK shell pane; **Q** quits; Escape leaves the artwork view.

Kitty/iTerm use LOOK's existing native image preview. Other terminals get an ASCII
preview using the existing image renderer (chafa/ffmpeg where available).
The local collection can still be listed and viewed when the node service is
unavailable. Online search and mutations require the node service.

## Web gallery

Open `/museum` in either chat. Collection, Discover, Favorites and Slideshow share
the selected owner; the browser remembers its owner independently of the terminal.
The page shows artist, date, source museum and downloaded status. Opening a work
shows its description and museum record link. The web host's existing endpoint
authorization protects the gallery and `/api/museum` gateway.

**Keep offline** saves on the selected owner. **Copy to this host** copies one work
to the computer serving Signal/Albert. **Copy collection to this host** performs a
background, checksum-verified copy of up to 1000 saved works and switches the
view to the local host. This is not a browser/phone download or a service-worker
cache. A web browser still needs its Signal/Albert host reachable.

## Offline copies and the shared saver

```sh
lk museum sync --node YOUR_COLLECTION_OWNER
lk museum status --node local
lk museum slideshow
lk saver Museum --preview
```

`sync` copies a collection into the endpoint's own local store. It does not delete
local work, overwrite existing favorites, or require the remote owner for later
viewing. Individual `pin ID` uses the same verified copying path. These are explicit
snapshots, not continuous background replication.

**Museum** is one entry in the existing shared visualizer/saver collection. The
graphical saver displays full images with captions; terminal music visuals render
ASCII versions from the same local collection. No network work runs in the saver
or animation loop. Artwork changes every twenty seconds. Existing saved enabled-
visual selections remain unchanged; enable Museum if a custom selection omits it.

## Storage and backup

- Catalog, favorites, rights, source IDs, checksums and job state:
  `~/.local/share/future-crash-look/museum.json`
- Downloaded images:
  `~/.local/share/future-crash-look/museum/images/`
- Disposable terminal remote previews:
  `~/.cache/look/museum/`

The catalog is already included by Fabric's essential-state recovery inventory.
The image directory is **not** included in that size-limited recovery capsule.
Include it in the archive computer's normal FabBack media backup sources to back
up the actual images; this feature does not silently change existing backup jobs
or claim that an image backup has completed. The retained source IDs also allow
re-downloading works that remain available from their museums.

## Sources and rights

- [The Met Collection API](https://metmuseum.github.io/): uses the paginated
  `/v1.1/search` endpoint and checks each object's `isPublicDomain` flag and image.
- [Art Institute of Chicago API](https://api.artic.edu/docs/): searches public-domain
  works and checks `is_public_domain` and `image_id` before saving.

Only public-domain/CC0 images identified by those providers are imported. Records
retain source identity, museum attribution, rights label, original record link
and image checksum. Artwork URLs are restricted to those museum hosts, including
redirects; arbitrary URLs or SVG uploads are not accepted. Artvee and The Last
Museum are not scraped or represented as supported APIs in this release.
