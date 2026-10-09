# LOOK notebook

The notebook keeps notes, tasks, and reminders in one local workspace. Every
paired node receives its own copy. Captures work offline; the node daemon exchanges
missing revisions every 15 seconds while peers are reachable. Large collections
catch up over several bounded batches. The existing Unix `ln`, LOOK tree `lkt`,
and recent `lkr` commands keep their meanings.

```sh
lkn Check remote video discovery
lkn --project LOOK --task Test Linux playback
lkn --task --due tomorrow Test metadata
lkn --remind "Saturday 9am" Test Linux playback
lkn --remind "in 10 minutes" --target Mac,3090 Check download
printf 'First line\nMore detail\n' | lkn --stdin --project LOOK
lk notes list
lk tasks list
lk reminders list
```

Notebook command keys use bold cyan accents, with subdued action labels and
metadata. The palette is shared by the list, note view, quick editor and help footer.

Bare `lkn` opens the notebook. Arrow keys move; Shift-arrows page or jump to
ends; Tab marks; Shift-A selects all filtered records. Type to filter or use `/`.
Typing filters titles and projects. `/` toggles full-text search across note
content while keeping your query; the footer says FILTER or SEARCH. Add
`\word` to exclude a term in the active scope, e.g. `LOOK \old`.
Shift-F cycles updated, created, title, project, due/reminder, and type sorting.
Shift-T cycles all records, notes, tasks, and reminders. Each row includes
creation and latest-edit timestamps; changes to a note retain its creation time.
Enter opens a boxed, scrollable Markdown view. E opens a quick body editor;
Enter saves, Shift-Enter/Ctrl-J inserts a newline, and Escape cancels. The title
stays stable so named notebooks are easy to reopen. V opens the same document
in `$VISUAL`, `$EDITOR`, Neovim, or vi. Escape returns to the filtered list.
If another node changes a note during quick editing, the draft is preserved
locally under `~/.local/share/look/notebook/drafts/` instead of overwriting it.
Shift-N opens quick capture: Enter saves; Shift-Enter adds a line break or a
blank paragraph; Escape cancels. The editor requests modified-key reporting
while active. If a terminal sends Enter and Shift-Enter identically, use Ctrl-J
or Alt-Enter for a newline. Cursor keys and Backspace edit the draft.
Shift-Left/Right jumps to the start/end of the note; Home/End moves within
the current line. Shift-Up/Down and Page Up/Down move a page of lines.
The read-only view also accepts Shift-arrows to page or jump to its ends.
Shift-P files under a project, Shift-C completes,
Shift-R schedules a reminder, and Shift-D deletes after confirmation. Escape
clears a filter, then exits. Ctrl-C exits immediately.
Press **H** or **?** for an in-app help page. It explains what File, Done,
Remind, and Delete change, with command examples. Escape closes help and retains
your filter and selection. `lkn --help` lists all flags and the same explanations.

LO can list or read records directly: `lo list the notes`, `lo what do our notes say`,
or `lo what does the first note say`. First/second refers to the current LKN
listing, ordered by most recent update. `notebook_list` needs no keyword;
`notebook_read` retrieves full text by ID or list position. Empty
`notebook_search` also lists records.

Use the eight-character ID printed after capture for these actions:

```sh
lkn show NOTE_ID
lkn edit NOTE_ID
lkn file NOTE_ID --project LOOK
lkn done NOTE_ID
lkn snooze NOTE_ID "in 20 minutes"
lkn delete NOTE_ID
lkn sync
lkn list --all
```

`NOTE_ID` is a placeholder for your saved note's ID. Add `--json` for structured
output. `--target all` is the default; named nodes or a comma-separated group
limit notification delivery. `--target local` resolves the current Fabric node
name through the running daemon. Offline, use an explicit name.

Reusable notes need no flags: `lkn To Do`, `lkn Scratch Pad`, or `lkn Notes`
creates the record on first use and reopens the exact title on later calls.
On a terminal it opens the inline view; piped output prints the document, and
`--json` prints its record. Names ignore case and repeated spaces. If more than
one record has that title, choose one in the notebook or use an ID. `lkn new To Do`
always creates a new record. Capture flags such as `--task`, `--remind`, or
`--project` continue to request a new structured capture.

Each reminder occurrence has the same ID on all replicas. Each targeted node
records its local delivery once and pulses the existing beacon. Albert and
Signal show a reminder card with Done, Snooze 10 minutes, and Open note. Late
reminders are marked overdue. Acknowledgment synchronizes to other nodes when
they reconnect; an offline screen can retain a reminder until then. Future Crash
also shows a reminder notice in its workstation, refreshed by the health poll.
From its shell, `lkn done NOTE_ID` acknowledges it.

Markdown documents live in `~/.local/share/look/notebook/notes/`, with immutable
revisions alongside them in `revisions/`. They remain readable by ripgrep. Editor
changes are imported before synchronization. Stable IDs survive filing and
renaming. Concurrent edits are preserved as separate conflict documents, and
automatic reminders pause for conflicted records. Read both versions and reconcile
with `lkn resolve NOTE_ID "reconciled text"`; deletion markers prevent stale
replicas from resurrecting deleted records.

Dates accept `today`, `tomorrow`, `Saturday 9am`, `Saturday at 9am`, or ISO date/time.
Durations accept `ten minutes`, `10 minutes`, or `in 10 minutes`, plus numeric
seconds, hours, days, and weeks. A bare clock such as `9am` or `15:30` means its
next local occurrence.
Local dates are interpreted on the capturing device and stored as absolute times.
Task due dates organize work; add `--remind` when an alert is required. Recurring
calendar events are outside this initial notebook feature.
