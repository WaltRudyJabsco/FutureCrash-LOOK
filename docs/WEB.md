# The reading desk

`lk web` is a keyboard launcher for browsers you already have. It starts inside
LOOK's current terminal palette, with a small reading shelf, your own bookmarks,
a browser-specific key guide, alternating rows and the usual selected-row highlight.
It does not fetch pages until you choose one, and needs neither Kitty nor a model.

- Up/down select; Shift-up/down page; Shift-left/right go to the ends.
- Enter reads the selected link. Quit the terminal browser to return to the desk.
- `b` cycles installed browsers and remembers your choice on this computer.
- `u` opens an address; `s` searches using DuckDuckGo's HTML search.
- `a` adds a bookmark: enter its address, then edit its prefilled name.
- `y` copies the selected link as Markdown for pasting into a Notebook note.
- `h` opens a local home page containing the shelf, bookmarks and search form.
- `q` or Escape exits the desk. Escape cancels an address or bookmark prompt.

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
Bookmarks and the chosen browser are local to the current user under
`~/.local/share/look/web/`. Existing browser bookmarks, sessions and keymaps
are not imported or replaced. The guide describes the browser's default keys;
personal keymaps may differ.

## Link hints

Lynx and Links launch with numbered links: type a number and Enter to follow.
Qutebrowser uses `f` and letter hints to open links. Chawan is a true terminal
browser with letter hints: `f`, type the letters, then Enter. Chawan's hint
alphabet can be customized in its own configuration. w3m shows link numbers
and supports Tab/Enter navigation; its guide does not promise numeric jumps.

Qutebrowser is explicitly marked **graphical window**. It opens a normal
qutebrowser session, using your existing configuration; quitting or handing off
to an existing instance returns control to the desk. LOOK's generated home page
follows Paper/Neon/Slate/Custom, but qutebrowser's chrome and remote websites
keep their own styling. Terminal browsers have limited support for modern
script-heavy sites; select qutebrowser when you need its graphical web engine.

w3m and Lynx use terminal-default text/background with ANSI link colors. Links
uses a light or dark ANSI background according to the selected LOOK palette.
Color overrides last only for that invocation. `--native-style` keeps the
browser's appearance; link numbering remains enabled. LOOK does not rewrite
personal browser configuration or key bindings.

You can run `lk web` in LOOK's adjacent shell pane. Exit the browser to return to
the desk, then exit the desk to return to that pane's shell. Existing pane focus
and close shortcuts remain unchanged.
