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

## Library and collections

**Library** contains saved works on the selected owner. **Discover** searches the
Met or Art Institute online, not your saved library. **Collections** are named
groups of saved works; a work can belong to several without duplicating its image.
**Favorites** is a quick personal selection. Starter-pack subject labels remain
source metadata, separate from the named collections you create.

The desk and web host remember the owner’s catalog. When that owner is offline,
you can still browse its metadata and open images already saved or cached on this
device, including the Museum saver cache. The offline indicator reports how many
images are available; the offline-only filter hides unavailable originals.
Discovery and changes to the owner require reconnection.

## Terminal controls

- Arrows select artwork; Shift+Up/Down (or Page Up/Down) moves a visible page;
  Shift+Left/Right (or Home/End) jumps to the beginning/end. These work in the
  image viewer too, within downloaded works.
- **1/2/3/4**: Library, Discover, Collections, Favorites.
- **c**: create a named collection; **m** adds/removes the selected saved work.
- **o**: show only images available offline here.
- **u**: keep the current view on this device, after confirmation.
- **F** (Shift+F): cycle Title, Artist, Century, Museum and Shuffle sorting without losing
  the selected artwork. Century uses the supplied date, oldest first; unknown
  dates sort last. Discovery sorting applies to the current results page.
- **Enter**: view a downloaded work; Left/Right (or Up/Down) cycle through
  downloaded works in the current list, wrapping at either end; **i** switches native image/ASCII preview.
- **d**: discover online; **t** changes Met/Art Institute source.
- **/**: search the current collection or discovery view; **n/b** pages discovery.
- **l**: return to the saved collection; **r** refreshes status.
- **K**: save the selected result on the library owner.
- **k**: copy a saved owner artwork to this endpoint.
- **f**: toggle a saved work's favorite flag.
- **a**: choose a starter download size (Enter cancels).
- **W**: standard LOOK shell pane; **q** quits; Escape leaves the artwork view.

**s** starts a slideshow of the current list or filtered search results. In the
artwork view, Space pauses/resumes it; arrows step manually and Escape returns to
the list. Slides advance every ten seconds and skip undownloaded discovery results.
Choose **Shuffle** with F for random order: each work appears once per pass, then
the next pass reshuffles without immediately repeating the last work. This also
applies to a selected collection or filtered list.
This differs from `lk museum slideshow` / `lk saver Museum`, which use the separate
full-screen saver and the endpoint’s locally saved collection.

Moving through the list shows a thumbnail and labeled artwork details beside it
(below it in narrow terminals), with alternating rows and a theme-aware selection.
Kitty/iTerm use LOOK's existing native image preview. Other terminals get an ASCII
preview using the existing image renderer (chafa/ffmpeg where available).
The local collection can still be listed and viewed when the node service is
unavailable. Online search and mutations require the node service.

## Web gallery

Open artwork supports Left/Right arrows and Previous/Next buttons, wrapping within
that view's displayed collection, Favorites, search results or offline filter.
The counter shows your position. Slideshow supports Left/Right, Space to pause/play,
F for fullscreen and Escape to exit; buttons show the shortcuts. Text-entry fields
retain their normal keyboard behavior.

Background refresh preserves existing artwork elements rather than reloading images
on each progress check. Only an active download shows a progress bar and Stop
control. Complete, cancelled, interrupted and below-target jobs show a finished
summary; for example, 707 of 1,000 is a result count, not an active download.
Source errors remain available under Source details. The paper gallery uses brass
navigation and progress accents with blue links and search controls.


Open `/museum` in either chat. Library, Discover, Collections, Favorites and Slideshow share
the selected owner; the browser remembers its owner independently of the terminal.
The page shows artist, date, source museum and downloaded status. Opening a work
shows its description and museum record link. The web host's existing endpoint
authorization protects the gallery and `/api/museum` gateway.

**Save to owner** downloads to the displayed library owner. **Keep on this host**
copies a work to the computer serving Signal/Albert. **Keep this view on this host**
performs a background, checksum-verified copy of the currently filtered saved works,
including their named collection memberships. It leaves the selected owner unchanged.
The confirmation names the destination. This is not a browser/phone download or a
service-worker cache: a web browser still needs its Signal/Albert host reachable.

Use **New collection**, the collection selector and each card’s membership action
to organize saved works. **Available offline on this host** filters cached images.
**Shuffle slideshow** randomizes the current view, including a selected collection,
with every work shown once before reshuffling.

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

**Museum** shows original images; **ASCII Museum** gives them a muted, shaded
text-art treatment. Both are entries in the shared visualizer/saver list.
Each graphical display selects a different artwork and color treatment using a
shared clock and display slot (distinct works require enough available images).
Artwork changes every twenty seconds. C changes colors; V changes visualizer.

The graphical saver prepares artwork from the configured Museum owner in a
background worker. It warms twelve images, then rotates through the owner's
collection, retaining at most 64 works / 256 MiB in
`~/.cache/look/museum-saver/`. Downloads are checksum-verified. Cached and locally
saved artwork remain usable offline; an empty cache needs the owner reachable
once. Network requests never block the drawing loop. This disposable cache is
not a pinned collection or a backup; use `lk museum sync` for a complete local copy.
Existing custom enabled-visual selections stay unchanged; enable either Museum
entry in the picker to include it in Cycle.

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

## Assistant and saver controls

LO's shared tool registry includes read-only `museum_search`, returning actual
collection metadata, owner-scoped image links and the gallery route. Metadata
alone is not a visual inspection of an artwork.

In both Museum saver modes, Right advances to the next display set and Left goes
back. Each set steps by the number of displays, keeping their artwork distinct
when enough images are available. Escape exits; C changes colors; V changes the
shared visualizer. Number Station (large held digits) and Prism Grid (diagonal
bands, checkerboards and diamonds) are also available in the shared saver/player
list. Enable them in an existing custom Cycle selection if desired.

## Museum-selected highlights

Press **h** in the terminal desk or **Download museum highlights** in the web
gallery to build two named collections on the displayed library owner:

- **Met Highlights:** objects flagged `isHighlight` by the Met.
- **Art Institute Featured:** works flagged `is_boosted` by the Art Institute.

Each targets up to 500 downloadable public-domain works in source search order.
These are museum-selected highlights, not a measured visitor-popularity ranking.
The selection methods are documented by the [Met](https://metmuseum.github.io/)
and [Art Institute](https://api.artic.edu/docs/).

```sh
lk museum featured
lk museum featured --source met --count 500
lk museum featured --source aic --count 500
lk museum status
lk museum cancel
```

The existing 3 GiB library budget applies. Existing images, favorites and other
collection memberships are preserved. Rerunning reuses the same named collections
and images. Progress counts include reused works, and report the actual total per
source. A shortfall is marked partial; source errors remain visible. No unrelated
works are added to fill a quota. Open Collections after refreshing to browse,
shuffle or keep an offline copy of either selection.

Download progress refreshes every five seconds in the terminal and web gallery.
Bars show saved/reused works against the requested target, with per-museum counts
for highlights. Partial jobs keep their actual percentage; source errors remain
visible. Pressing h again during a highlights job shows its existing progress.

## Curate while viewing

Artwork and slideshow views keep the selected image visible while you curate:
**f** favorites it, **k** keeps a copy here, **m** adds/removes collection membership,
and **x** marks it for removal or undoes that choice. Actions pause playback so
an advancing slideshow cannot move the target underneath you. **c** still creates
a collection from the desk; name it, then use **m** on any saved work.

**F while viewing** opens a native fullscreen image window on the display under
the pointer. It uses the installed saver graphics runtime (`lk saver setup` if
needed), fits the whole image without cropping, and supports arrows, Space, f/p/m/x,
F to toggle windowed/fullscreen, and Escape to return. Shift+F in the list continues
to change sorting. Browser artwork details and slideshows have Fullscreen buttons
and the F shortcut, plus the same curation actions as the grid. Browser fullscreen
availability depends on the browser/device.

## Removal review and daily discovery

Thumbs-down (**x**, or the browser button) hides a work from normal browsing and
schedules removal of its image **on the library owner after 48 hours**. It clears
its favorite flag. **5 / Removal review** shows marked works; x/Undo removal cancels
the deadline. Favoriting a marked work also cancels removal. The catalog record and
collection memberships remain, preventing starter packs, highlights and refills
from silently downloading rejected artwork again. After expiry, undo allows a
new explicit download; it cannot recover deleted image bytes by itself.

The node checks deadlines once a minute while running. If it was offline at the
deadline, cleanup occurs when it next starts. Independently kept copies, caches on
other devices and existing backups are not erased by this owner-local action.

**j** in the desk, **Daily refill** in the browser, or
`lk museum rotation on --node YOUR_OWNER` enables daily discovery on that owner.
Use `off` to disable it. Fresh installations leave this option off. Once enabled,
it checks about once every 24 hours and fills toward **1,000 kept images**, adding
at most **100 new works per day**. It never deletes artwork to enforce that target,
never evicts favorites, respects the 3 GiB budget, and skips every existing catalog
ID, including rejected works. It searches the starter subjects with a rotating
first subject; refills are discoveries, not popularity-ranked selections. Partial
jobs and source errors use the same progress display. The schedule persists across
restarts and waits for any active download job to finish.


### Favorites and a fresh discovery pool

The default **To explore** view hides favorites and rejected works. **👍** saves
an artwork to **Favorites**; removing that mark returns it to the pool. **All works**
shows favorites and undecided artwork together. Collections remain independent.
The browser uses compact, accessible thumb buttons in cards, detail, and slideshow
controls. In the terminal, **f** toggles favorites, **1** opens To explore,
**4** opens Favorites, and **6** opens All works. **x** retains the 48-hour removal
and undo behavior.

Daily refill targets 1,000 undecided works in addition to favorites. Favorites stay
on disk and remain excluded from duplicate downloads. The existing maximum of
100 additions per daily run and 3 GiB collection budget still apply, including
favorite images. Rating does not trigger an immediate download.

## Print an artwork

Press **p** in the terminal list, artwork viewer or fullscreen viewer to print
that work. **Shift+N** also works, matching LOOK's file-print shortcut. **k** keeps
an offline copy here; **K** saves a discovered work on the library owner.
In the web gallery, use **Print** on a card, in the viewer or in the slideshow.

The chooser prefers an available receipt printer, while keeping all discovered
printers available. Review the destination and estimated paper length, then
explicitly print one copy. Receipt images use the printer's configured encoder
and the existing 25 cm limit. Opening the chooser or reviewing a plan prints
nothing; cancel discards an unsent plan. Printer errors are never retried
silently. Current file input limit is 3 MiB; larger artwork needs a smaller export.
