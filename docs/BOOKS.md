# Books

`lk books` (alias `lk bk`) opens a dedicated EPUB/PDF shelf. It shares the Fabric
and media-root configuration, but does not insert documents into MP/TV queues or
send them to mpv. Install an EPUB/PDF reader appropriate for your OS; Enter uses
system defaults, including the existing PDF application preference.

## First book

- Put existing EPUB/PDF files in the configured media owner's `books` directory,
  then run `lk books scan` or press **R** in the shelf.
- Or run `lk books import "/path/My Book.epub"`. Import copies the original and
  refuses a conflicting filename. The source is retained.
- Use **g** to search Project Gutenberg. Select a result and confirm its download
  to the configured media owner. **Esc** returns without importing.

No account-specific paths, machine names or drives are assumed. The default for
a fresh account is `~/Media/books`. The existing media destination chooses the
owner; `--node local` or `--node NAME` overrides it for imports, scans and fetches.
For example, `lk books --node my-server` opens the shelf on this computer while
new imports and Gutenberg downloads go to that paired server's books folder.
The shelf header shows the current import owner.
An empty shelf does not scan the home directory or initialize attached drives.

## Shelf controls

| Key | Action |
| --- | --- |
| Arrows / Shift-arrows | Select / page and ends |
| `/` | Search title, author, shelf or format; Enter returns to browsing |
| Enter | Open the book in a reader |
| `s` | Cycle All, To Read, Reading, Finished and custom shelf filters |
| `m` | Cycle the selected book's reading state |
| `e` | Edit prefilled title, author, custom shelf and reading-position label |
| `i` | Import a file; Tab completes and arrows open the existing path picker |
| `g` | Search Gutenberg; Enter offers import confirmation |
| `k` | Keep a permanent local library copy for offline reading |
| `y` | Copy a Markdown file/Fabric link for Notes |
| Shift-R | Scan the configured books folder and refresh the Fabric shelf |
| Shift-G | Reverse order |
| Shift-W | Open the existing sibling shell pane |
| `?` | Expand controls in narrow panes |
| Esc | Leave results, clear search, then close the shelf |

Opening a remote book makes a verified cache copy (up to 100 MiB). **k** places a
permanent copy in this computer's own books folder instead. Cataloged ownership
does not guarantee current reachability. If a peer is unavailable, a cached shelf
can retain its entries, but opening them still requires a local copy or a live
owner. No Bluetooth/output routing changes are involved.

Reading states and metadata belong to the owning catalog. Editing does not
rewrite or rename document files. Identical content shares a book ID; rescans and
renames retain reading state. Reading-position labels are manual: this release
does not extract progress from external readers or synchronize their bookmarks.
PDF metadata uses optional `pdfinfo`; without it, filenames remain useful titles.
EPUB metadata is read from the package. Protected/unsupported books may require
their own authorized reader; LOOK does not remove protection.

## Commands

```
lk books
lk bk
lk books list --json
lk books scan --node local
lk books import "/path/My Book.pdf" --node local
lk books search "Pride and Prejudice"
lk books fetch https://www.gutenberg.org/ebooks/1342.opds --node local
```

Search is explicitly online and uses [Project Gutenberg's official OPDS catalog](https://www.gutenberg.org/ebooks/offline_catalogs.html).
Fetch accepts direct public HTTPS EPUB/PDF links (including suitable Internet
Archive download links) or Gutenberg OPDS entries. It does not automate borrowing,
subscription authentication or protected downloads. Downloads and remote copies
are bounded at 100 MiB; malformed/oversized metadata is rejected.

**Notes:** paste the link from **y** into an existing note. It uses the ordinary
`@node:/path` convention, with readable labels and spaces handled by the existing
Markdown link builder. There is no new book-link protocol.
