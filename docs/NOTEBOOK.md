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
metadata. The list leads with bold titles, colored note/task/reminder types,
project labels and subdued IDs/timestamps. Title, Type and Project columns resize
with the terminal, giving remaining space to the title. Narrow panes drop Project,
then Type; long values stay within their column with an ellipsis. IDs, dates and
alerts sit on the supporting line. Enter opens the complete note title and body.
Alternating rows remain subtle; the
selected record retains contrasting alert and detail colors. Wrapped command
keys, including arrows and Shift-F, keep their accent color.

Bare `lkn` opens the notebook. Arrow keys move; Shift-arrows page or jump to
ends; Tab marks; Shift-A selects all filtered records. Type to filter or use `/`.
Typing filters titles and projects. `/` toggles full-text search across note
content while keeping your query; the footer says FILTER or SEARCH. Add
`\word` to exclude a term in the active scope, e.g. `LOOK \old`.
Shift-F cycles updated, created, title, project, due/reminder, and type sorting.
Shift-T cycles all records, notes, tasks, and reminders. Each row includes
creation and latest-edit timestamps; changes to a note retain its creation time.
Enter opens a boxed, scrollable Markdown preview. Heading marks disappear
into cyan headings; **bold**, *italic*, ~~strikethrough~~, bullets, numbered
lists, task checkboxes, quotes, links and inline/fenced code are rendered.
Links retain their destination as visible text. Code preserves literal marks.
This is a lightweight terminal preview; tables and HTML remain plain text.
E opens a quick body editor with the original Markdown marks;
Enter/Ctrl-J inserts a newline, Shift-Enter/Ctrl-S saves, and Escape cancels. The title
stays stable so named notebooks are easy to reopen. V opens the same document
in `$VISUAL`, `$EDITOR`, Neovim, or vi. Escape returns to the filtered list.
If another node changes a note during quick editing, the draft is preserved
locally under `~/.local/share/look/notebook/drafts/` instead of overwriting it.
Shift-N opens quick capture with the same newline/save controls; Escape cancels. The editor requests modified-key reporting
while active. If a terminal sends Enter and Shift-Enter identically, use Ctrl-S
to save. Cursor keys and Backspace edit the draft.
Shift-Left/Right jumps to the start/end of the note; Home/End moves within
the current line. Shift-Up/Down and Page Up/Down move a page of lines.
The read-only view also accepts Shift-arrows to page or jump to its ends.
After `lk transcribe setup`, Ctrl-D starts dictation inside the quick editor.
Ctrl-C finishes recording and inserts the transcript at the caret; review it,
then save normally. Uppercase D remains text inside the editor. See
[Local speech input](TRANSCRIPTION.md) for platform details and recovery.

Shift-P files under a project, Shift-C completes,
Shift-R schedules a reminder, and Shift-D deletes selected or marked records
after typing `yes` at confirmation. Deletion markers synchronize to paired nodes. Escape
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

For example, edit a note to contain:

```markdown
# To Do
## Today
- [ ] Buy **milk**
- [x] Read the *Notebook guide*

Use `lkn To Do` to reopen it.
```

The preview shows headings without hashes, readable emphasis and ☐/☑ task
markers. Shift-Enter/Ctrl-S saves an edit and returns to that preview. Formatting never
rewrites the saved Markdown or the file opened by V.

LO can edit existing records: ask “Add buy milk to To Do,” “Rewrite the Scratch
Pad note,” or “Move the call reminder to tomorrow.” It reads the record first
and supplies that revision to `notebook_update`; stale or conflicted edits are
rejected. Appending keeps the title, project and schedule. Rescheduling changes
only the requested field. Conservatively configured LO remains read-only.

Reminders now request native desktop notifications and sound on each targeted
node, even when no browser or dashboard is open. Operating-system permissions
and an audio/session backend still determine presentation. Delivery failures
are recorded; the persistent reminder card remains available for Done/Snooze.
Future Crash adds a reminder cue while its sound chip is enabled. Albert and
Signal have an Enable browser sound / notifications button; the browser needs
that gesture and permission for its own sound/notification channel.

```sh
lk notifications
lk notifications voice on --node 3090
lk notifications sound off
lk notifications desktop off
```

Speech is off by default. Targeted nodes deliver each occurrence once; snoozing
creates a new occurrence. Browser alerts likewise deduplicate an occurrence
within the open page. Visual reminder cards persist until completion or snooze.


## Runnable project commands

A note can keep reusable terminal commands beside project files, folders, URLs
and related notes. In E (quick edit) or V (full editor), add an explicit, closed
`command` fence:

````markdown
```command
lk help all
```

```command label="Open manuscript" cwd="~/Projects/My Book"
nvim manuscript.md
```
````

Ctrl-K now starts in **Link** mode as before. **Ctrl-T** switches the helper to
**Command** mode, prefilled from the clipboard. The fields become Command,
Label and Working directory (optional), so a path containing spaces is never
mistaken for executable code. Paste multiline command text into Command; Enter
adds a newline there. Tab moves to Label and then Working directory. Use
Shift-Enter/Ctrl-S to insert the finished block; Enter in the last field also
inserts it. Save the note as usual afterward. Ctrl-T switches back to Link and
preserves both drafts; Ctrl-N's note picker stays available in Link mode.

The helper supplies quoting and a suitable Markdown fence, even when the pasted
script contains backticks, and inserts it on its own lines. Creating the block
never runs it. You can edit its source later with E or V.

The rendered preview shows **Run: Open manuscript [2]**, using the same numbering
as Markdown links in document order. Press its number (1–9) or L to choose from
all links and commands, including multi-digit entries. Selection opens a preview
of the exact command and resolved working directory. Scroll if needed; **R** runs
it and Escape cancels. Enter alone does not execute it.

Commands run locally in the terminal with the current account, inherited PATH
and the user's `$SHELL` (or `/bin/sh`), using noninteractive shell syntax.
Pipelines and multiline commands work; shell aliases/functions that exist only
in an interactive startup file may need an executable command instead. Full
screen programs such as Neovim receive the ordinary terminal. When the command
finishes, its exit status is shown; press Enter to return to the same note.

`label` and `cwd` are optional quoted header fields. Without `cwd`, the command
runs from the directory where Notes was launched. `~` expands to the current
user's home; an explicitly relative `cwd` starts beside the note file, like
relative file links. The directory must exist locally. `@node:/path` remains a
Fabric file link, not a command working directory.

Only `command` fences are runnable. Ordinary `sh`, `bash`, `python` and unmarked
code blocks stay examples. Unclosed, empty or invalid command blocks cannot be
selected. Terminal controls and hidden directional controls are rejected before
execution. Previewing, editing, copying, syncing and opening a note never run
its commands; each execution requires the explicit R confirmation.

## Adjacent shell pane

Press **Shift-W** from the Notes list or a rendered note preview to open
a sibling shell in the current working directory. Your selection, filter and
scroll position stay in the original view. In Kitty, **Option-Shift-W** on Mac
(**Alt-Shift-W** on Linux) switches focus, and **Ctrl-Shift-W** closes the focused
pane. In tmux, **Ctrl-B then O** switches; `exit` closes the shell. These hints
remain visible after opening a pane. The terminal owns the sibling shell.

The views redraw to fit the terminal after panes open or close. Shift-W stays
ordinary text inside note editors and URL/bookmark prompts. In a launched web
browser, the browser owns its keys; quit back to the desk to use Shift-W.
Without Kitty or tmux, LOOK explains the requirement and stays in your view.
