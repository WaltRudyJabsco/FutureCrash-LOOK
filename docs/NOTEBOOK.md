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

Bare `lkn` opens the notebook. Arrow keys move; Shift-arrows page or jump to
ends; Tab marks; Shift-A selects all filtered records. Type to filter or use `/`.
Enter opens the focused Markdown document in `$VISUAL`, `$EDITOR`, Neovim, or vi.
Shift-N opens quick capture: Enter saves; Shift-Enter adds a line break or a
blank paragraph; Escape cancels. The editor requests modified-key reporting
while active. If a terminal sends Enter and Shift-Enter identically, use Ctrl-J
or Alt-Enter for a newline. Cursor keys and Backspace edit the draft.
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

Dates accept `today`, `tomorrow`, `Saturday 9am`, `in 10 minutes`, or ISO date/time.
Local dates are interpreted on the capturing device and stored as absolute times.
Task due dates organize work; add `--remind` when an alert is required. Recurring
calendar events are outside this initial notebook feature.
