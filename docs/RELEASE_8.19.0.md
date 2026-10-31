# 8.19.0 — Terminal reading and stable preview frames

Bundle/node/Albert integration **8.19.0**; LOOK **4.66.0**.

Enter in Books uses optional Bookokrat in the current terminal and its reading
view. Quit the reader with q to return to the shelf. System reading remains
available with o and an explicit preference. Reader setup is local to the reading
computer; library ownership remains controlled by --node. New installs offer the
optional Homebrew/Linuxbrew dependency, and existing installations can use
`lk books reader install` or the first-use setup choice.

Setup supports only Bookokrat, requires explicit confirmation and reports durable
status. It does not expose a general remote shell or arbitrary package names.
Existing Bookokrat preferences/bookmarks are preserved. Positions are reader-local,
not automatically synchronized across the Fabric. See [Books](BOOKS.md).

Media availability checks now redraw only when their state changes. Kitty native
preview deletion, text drawing and cached-image restoration are synchronized as
one visible frame. This addresses the remaining ASCII/native flicker caused by
otherwise-identical reachability checks and separate output flushes. Other
terminals retain their existing rendering path.

Validation: 170 targeted checks passed, including a real Bookokrat EPUB terminal
handoff/return, paired HTTP setup routes, reader setup/update coordination, native
preview frame presentation, availability changes, search input ownership and
release/installer checks. Generated command references and shell syntax checks
also passed.
