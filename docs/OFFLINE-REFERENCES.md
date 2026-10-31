# Offline references

`lk wiki` opens an owner-aware Kiwix ZIM library. It uses the same configured
media owner as Books, with `--node local` or `--node NAME` to override. The local
reference folder defaults to the owner's configured media root plus `reference`,
or `~/Media/reference` on a fresh installation. It never scans the whole disk.
Existing `.zim` files in that folder are available without downloading again.

```
lk wiki
lk wiki setup --node my-server --confirm
lk wiki catalog wikipedia --node my-server
lk wiki fetch CATALOG-ID --node my-server --confirm
lk wiki jobs --node my-server
lk wiki cancel JOB-ID --node my-server
lk wiki configure --root "/path/reference" --node my-server
lk wiki search "coral reef" --archive ARCHIVE.zim --node my-server
lk wiki status --json
```

Setup installs only `libzim` into an isolated Python environment on the selected
owner. The terminal interface uses **i** and a confirmation prompt. **d** opens
the official online catalog, **/** searches collections or the selected offline
archive, and Enter opens an archive/article or offers a download summary. The
summary names the collection, variant, approximate size, owner and destination.
Press **r** to refresh jobs and **x** to cancel an active download. Shift-arrows
page and jump to ends. In an article, **l** follows a numbered internal link,
**b** returns to the previous article and **y** copies the visible passage.
No network is needed for searches/articles when the owner and its ZIM are local.
A remote Fabric owner still must be reachable; keep an archive on a travelling
computer or attached storage for offline travel.

Kiwix `nopic` editions contain full articles without pictures. `mini` editions
contain article introductions and infoboxes, not full articles. `maxi` includes
pictures. Sizes and current IDs come from the live Kiwix catalog; none are pinned
to a private server or fixed date. The catalog also supports other collections,
such as those published for wikiHow, when available. They are offline snapshots,
not live websites, and retain their original licensing and attribution.

Downloads use official Kiwix metadata, HTTPS mirror fallback, byte limits, free
space checks and SHA-256 verification before publishing an archive. Existing
files are never intentionally replaced. Progress and errors are durable, and a
cancelled/interrupted `.part` file is retained for an explicit retry/resume.
Maintenance waits for active downloads and setup rather than killing workers.
No archive or background package installation starts just by opening the shelf.

The paired `/v1/wiki` API exposes the same status, catalog, setup, configure,
fetch, cancel, search and article actions. Setup/download require `confirm: true`.
This version supplies a terminal reader and JSON API, not a public web server.
See [Kiwix](https://get.kiwix.org/) and
[libzim](https://github.com/openzim/python-libzim) for archive provenance and APIs.
