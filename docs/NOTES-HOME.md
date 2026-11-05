# Notes as a Fabric home

`lknh` is the shell shortcut for `lk notes home`. Plain `lkn` still opens the
workspace. The first explicit Home open creates an ordinary editable note with a
stable reserved ID. Later opens preserve its content and title, even after a
rename. It uses the existing replicated notebook store, so it works offline.
A deleted Home is not silently resurrected. Concurrent offline creation/edits
can produce normal notebook conflicts; reconcile them explicitly rather than
choosing a version automatically. Existing unrelated notes titled Home are left
untouched.

The starter has Places, Projects, Research and Repeatable work sections. Its
numbered Places links open Museum, Mercury Reader, YouTube Radio, Printers,
Saver settings and Wiki. Quit those tools to return to the note. Edit with E;
Ctrl-K inserts a link, Ctrl-N finds a note, and Ctrl-A in the Link dialog picks a
Fabric tool. Ctrl-T switches between links, reviewed commands and live terminals.
A command can prompt for input; a terminal supports interactive programs. Opening,
reading or syncing a note does not execute either.

## Link and tool audit

| Target | Notes pathway | AI pathway / boundary |
| --- | --- | --- |
| Notes and projects | `note:FULL_ID`; stable after rename | notebook_list/read/update, with revision checks |
| Files/directories | paths, file URLs, `@peer:/path` | Existing file tools; remote paths need that peer |
| Mercury manuscripts | `mercury:PROJECT_ID` | Stable launch link; not a new manuscript editing tool |
| Museum | `look:museum` opens picker | museum_search returns actual catalog entries |
| Books | `look:books` opens Reader | books_shelf / books_lookup |
| YouTube Radio | `look:ytr` opens shared queue | radio_queue / radio_add; adding does not play |
| Printers | `look:print` opens print desk | printers_list / printer_inspect / print_prepare; review before paper |
| Wiki | `look:wiki` or `wiki:ARTICLE` | Article bookmark supported; no new AI navigation tool |
| Savers | `look:saver` opens settings | Human picker; no new AI launch tool |
| Custom commands | explicit command block | Inspect only; execution retains existing review |
| Interactive programs | terminal block | Inspect only; explicit terminal activation required |

`look:` links are a fixed catalog of interactive launchers, not arbitrary shell
URLs. They have no user-supplied command arguments. Book, artwork and radio item
IDs are available through the existing domain tools; this milestone does not
invent permanent item URLs from temporary streaming addresses.

## AI discovery and questions

- `notebook_home` reads Home without creating it and reports missing/conflicted
  state honestly.
- `notebook_actions` exposes the same portable links as the human picker, their
  terminal commands, available AI tools and useful follow-up questions.
- `notebook_links` inspects a note in numbered-link order, including command and
  terminal blocks. Every result explicitly reports that it was not executed.

When several targets match, ask using returned labels and resolve the response to
stable IDs. Call the actual domain tool for a requested action and report its
receipt. The catalog is discovery, not a universal executor: missing native AI
operations remain explicit. Custom note text is content, not permission to run a
command. Home conflicts report revision choices and the existing resolve command.

## Installation and rollout

The runtime changes use existing installed modules. `lknh` is a Zsh function,
like `lkn`, in LOOK's managed shell fragment. Fresh installs receive it normally;
managed runtime-only upgrades must also refresh that function in the managed
fragment with a backup. Existing shells need `exec zsh` (or a new terminal) to
load it. `lk notes home` works immediately after the runtime update.

## Albert's window into Home

Albert uses the shared LO tool path, so it can read Home and inspect its links via
the same notebook tools. No separate browser Home layout is imposed in this
milestone. The editable note remains the source of truth.

Albert conversation dismissal now persists against the exact server turn IDs,
including IDs migrated from older thread files. Refreshing the same session will
not restore those turns. Other turns and explicitly saved objects remain intact.
Browsers connected to the same Albert host/session share that dismissal; this is
not a new cross-host conversation replication system. Failed dismissal leaves the
card visible with an error rather than pretending it was permanently cleared.

Albert's response expression now uses a deterministic 96×32 dot matrix with eight
motifs and pixel lettering, selected from the request/response topic. Another
impression changes its variation. Gentle opacity motion respects reduced-motion
preferences; the matrix is an illustration, not a data display. This first version
has an extensible visual vocabulary, not model training or learned preferences.
Signal's expression system is unchanged.

## More tools in the link picker

In the note editor, press Ctrl-K, then Ctrl-A to browse all 24 supported Fabric
launch links. Type to filter names, destinations and descriptions. Use arrows or
Tab to select, Page Up/Down (or Shift-Up/Down) to move a page, and Home/End
(or Shift-Left/Right) to jump to either end. Enter inserts the selected link;
Escape returns without inserting. Number then Enter also selects a listed tool.
The footer uses the current theme's key highlights.

Alongside `notes`, `museum`, `books`, `ytr`, `print`, `saver` and `wiki`, the
`look:` catalog now includes:

| Destination | Opens |
|---|---|
| `look:files` | File browser |
| `look:tasks` | Tasks |
| `look:reminders` | Reminders |
| `look:mp` | Music library |
| `look:player` | Music player |
| `look:tv` | Video library |
| `look:visualizers` | Visualizer picker |
| `look:terminal` | Terminal themes |
| `look:lock` | PIN curtain settings |
| `look:web` | Web desk |
| `look:words` | Dictionary |
| `look:latin` | Latin reference |
| `look:games` | Games |
| `look:commands` | Searchable command reference |
| `look:system` | System overview |
| `look:ai` | AI settings |
| `look:albert` | Albert in your browser |

`lk notes actions --json` and the assistant's `notebook_actions` tool expose the
same catalog. These are reviewed entry points, not arbitrary `lk` commands with
arguments. Existing Home notes are not rewritten; new Home notes retain the
small starter menu. Add whichever tools suit your own page.
