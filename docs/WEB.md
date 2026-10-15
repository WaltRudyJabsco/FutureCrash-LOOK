# The reading desk

`lk web` opens a personal Markdown home backed by a real Notebook note.
The rendered page shows headings, prose and numbered links. The selected link is
highlighted, with its full target below the page. Nothing is fetched until you open it.

- Up/down or Tab select links; Enter opens; 1–9 open directly; `l` opens the full link picker.
- Shift-up/down or Page Up/Down scroll the note; Shift-left/right jump first/last.
- **`e` edits the displayed note**, using the Notebook quick editor. Enter adds a
  newline; Ctrl-S or Shift-Enter saves; Escape cancels. Ctrl-K inserts links,
  including picking another note. Delete or move Markdown lines to remove/reorder links.
- **`n` chooses an existing Notebook note as your home**. Search by title/project;
  no copying IDs. Home selection is local; the note uses normal Notebook syncing.
- `a` adds a named web bookmark to the home note, regardless of which linked note
  you are reading. `y` copies the selected Markdown link. `r` selects related notes.
- `h` returns to home. Escape returns from a linked note, then exits at the root;
  `q` exits directly. File/Fabric links use the existing Notebook handlers. Explicit
  command blocks retain Notebook's review and confirmation before execution.
- `u` opens an address; `s` searches DuckDuckGo's HTML search. `b` cycles installed
  browsers and remembers the choice; w3m leads on fresh installs when available.
- `t` toggles initial numbering; `?` shows the browser guide. `W` opens a shell pane.

On first opening the desk, Web creates a **Web Home** note under project **Web**,
with Google News, a starter reading shelf and copies of legacy bookmarks. This
migration happens once; old bookmark data is retained. The note becomes the
editable authority: changing or removing starter links works like any other note.
A deleted/conflicted home is not silently regenerated; choose another with `n`,
or explicitly create a replacement with `e`. Resolve conflicts in Notes.

`lk web home` exports the selected home to local HTML and opens it in the chosen
browser. Its rendered text is escaped; only HTTP(S) links become browser actions.
Use the terminal desk for note, file and command links. The HTML is a generated
view, so edit the Notebook note rather than the exported file.

```sh
lk web list
lk web https://example.org
lk web search terminal art
lk web --browser lynx https://example.org
lk web --browser qutebrowser home
lk web --native-style
```

The picker discovers w3m, Lynx, Links/Links2, Chawan (`cha`), and qutebrowser.
It does not install them. Missing browsers are listed by `lk web list`; a machine
with none installed can still manage bookmarks and copy links from the desk.
The home-note selection, legacy bookmarks and chosen browser are local under
`~/.local/share/look/web/`. Existing browser bookmarks, sessions and keymaps
are not imported or replaced. Web home content is stored and synced by Notebook. The guide describes the browser's default keys;
personal keymaps may differ.

## Link hints

Lynx and Links launch with numbered links: type a number and Enter to follow.
Qutebrowser uses `f` and letter hints to open links. Chawan is a true terminal
browser with letter hints: `f`, type the letters, then Enter. Chawan's hint
alphabet can be customized in its own configuration. w3m supports Tab/Enter
and LOOK's number-then-Esc-j selection while tags are visible.

Qutebrowser is explicitly marked **graphical window**. It opens a normal
qutebrowser session, using your existing configuration; quitting or handing off
to an existing instance returns control to the desk. LOOK's generated home page
follows Paper/Neon/Slate/Custom, but qutebrowser's chrome and remote websites
keep their own styling. Terminal browsers have limited support for modern
script-heavy sites; select qutebrowser when you need its graphical web engine.

w3m and Lynx use terminal-default text/background with ANSI link colors. Links
uses a light or dark ANSI background according to the selected LOOK palette.
Color overrides last only for that invocation. `--native-style` keeps the
browser's appearance. LOOK does not rewrite personal browser files. The w3m
session overlay reserves Esc-h, Esc-j and normal Enter; other personal bindings
are copied from its configured keymap.

You can run `lk web` in LOOK's adjacent shell pane. Exit the browser to return to
the desk, then exit the desk to return to that pane's shell. Existing pane focus
and close shortcuts remain unchanged.

## Adjacent shell pane

Press **Shift-W** from the Web reading desk to open
a sibling shell in the current working directory. Your selection, filter and
scroll position stay in the original view. In Kitty, **Option-Shift-W** on Mac
(**Alt-Shift-W** on Linux) switches focus, and **Ctrl-Shift-W** closes the focused
pane. In tmux, **Ctrl-B then O** switches; `exit` closes the shell. These hints
remain visible after opening a pane. The terminal owns the sibling shell.

The views redraw to fit the terminal after panes open or close. Shift-W stays
ordinary text inside note editors and URL/bookmark prompts. In a launched web
browser, the browser owns its keys; quit back to the desk to use Shift-W.
Without Kitty or tmux, LOOK explains the requirement and stays in your view.

## Reading without link tags

Numbered browsers start with tags off. Press **t** in the desk to remember tags
on/off for future launches, or use `lk web --tags on URL` / `--tags off URL` for
an invocation override. This controls w3m, Lynx and Links/Links2; Chawan and
qutebrowser retain their native temporary `f` hints, cancelled with Escape.

In w3m, **Esc then h** toggles tags. Type a number, then **Esc then j** to select
that numbered link; Enter follows it and hides tags again. Tab and Enter continue
to work. These session bindings use a temporary keymap overlay, retain unrelated
personal bindings, and never save to the browser config. The default applies only
to launches through LOOK.

Lynx changes numbering through `o` → Keypad mode. Links/Links2 use Escape → View →
HTML options → Links are numbered. These are native menu controls: LOOK does not
claim automatic post-navigation clearing or a shared in-page key for them. The
desk shows each browser's guide.

Hiding tags removes numeric clutter, not site navigation. Removing menus, cookie
prompts and repeated headers requires content extraction; this update does not
implement an article-reader view. Terminal text browsers have different rendering
capabilities from a graphical browser or a browser-engine-backed terminal viewer.

## w3m navigation keys

Once a page opens, w3m receives keyboard input directly. LOOK does not translate
arrow or Shift-arrow sequences or override page/Home/End navigation. Native and
personal browser bindings remain in effect. The desk itself retains LOOK's
arrow/Shift-arrow navigation. Link-tag shortcuts remain available in w3m.
