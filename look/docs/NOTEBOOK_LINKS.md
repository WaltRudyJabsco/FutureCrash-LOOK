# Notes, links, and paste

The quick editor uses **Enter** or **Ctrl-J** for a newline and
**Shift-Enter** to save. **Ctrl-S** also saves when the terminal cannot report
Shift-Enter. Escape cancels. Existing movement, paging, full-editor (V),
filter, sort, and marking shortcuts remain available.

Bracketed paste inserts the entire clipboard as text. Pasted Enter, Escape,
and Ctrl-S never act as editor commands. CRLF becomes LF, Unicode (including
emoji joiners) is preserved, and terminal controls appear as inert escaped
text. The editor enables bracketed paste while it owns input, then restores
terminal state when it exits. Ordinary multiline paste also keeps editing
because Enter no longer saves. Very large bracketed pastes are drained and
discarded to bound memory.

Markdown links appear as readable labels with numbered markers. Press 1–9
to open those links directly, or **L** to select any link using arrows/Tab or
a number followed by Enter. Escape returns from the selector.

Examples:

    [Project folder](</Users/me/Project Files>)
    [Source file](file:///Users/me/project/main.py)
    [Reference](https://example.com/reference)
    [Other note](note:0123456789abcdef0123456789abcdef)
    [Remote folder](<@3090:/run/media/me/2TB Storage>)
    [Remote file](<@3090:/home/me/project/main.py>)

Use the full stable note ID from the notebook record (lkn list --json).
Renaming or moving a note to another project does not change that ID.
Missing/deleted or conflicting note targets produce a readable message.
Relative file paths resolve beside the note's Markdown file.
Angle brackets allow spaces; balanced parentheses in targets are supported.
Code spans and fenced code blocks do not create active links.

Local file links open LOOK's file browser with the file selected; directory
links open that directory. URLs open the system browser. Remote links use
the existing paired-node /v1/files/browse gateway and @node:/path
convention. Directory links allow parent/child navigation. File links select
the file in its containing remote directory; Enter shows its location and
Y copies the Fabric address. This browser does not download a remote file
or launch it on another computer. Remote file rows require the updated node
runtime; older nodes still provide directory listings.

**B** shows related notes: records whose rendered Markdown links point to
the current note's full stable ID. This includes completed notes and derives
the result from current notebook content without a second database.

The player's seventh visual mode, Album Art, uses muted foreground accents.
A deterministic track/queue identity chooses the color, avoiding the previous
color on transitions, even for songs sharing an album cover. Pause, seek,
and redraw keep it stable; the six ambient modes keep their existing colors.

## Making links without looking up IDs

**Y** in the Notes list copies a complete Markdown link for the highlighted
record, using its title and full stable ID. **Y** in a note preview copies the
link to that note. Find a note with the existing filter, copy it, return to the
destination note, press E, and paste. No JSON or remembered IDs are required.
The same operation works for tasks and reminders. Copying does not edit records.

**Ctrl-K** in the quick editor opens Insert Link at the text cursor. It reads
a clipboard path, URL, Fabric address, or complete Markdown link, suggests a
label, and focuses that label. Type to replace the suggestion, or press Enter
to keep it and insert. Tab switches between target and label; arrows/Home/End
edit the current field. For manual entry, Enter accepts the target, then Enter
accepts the label. Escape closes the dialog without changing the draft.

For example: copy a directory path with Y in LOOK's file browser, return to a
note, press E then Ctrl-K, type "Mac project", and press Enter. The helper writes
the Markdown, including angle brackets for spaces. Save the note with
Shift-Enter or Ctrl-S as usual. Ordinary paste still inserts literal text.

**Ctrl-N inside Insert Link** opens a note picker. Type words from its title
or project, move with arrows, and press Enter. The selected title becomes the
suggested label and its full stable ID becomes the target. This includes
completed notes; conflicted records are excluded until resolved. Escape returns
to the link dialog. No IDs appear in the picker.

A copied note link can also go through Ctrl-K if you want to give it a different
label. Titles containing brackets or Markdown punctuation remain literal labels.
The editor still shows the final Markdown and IDs; the rendered preview shows
readable labels.

Clipboard reading uses pbpaste on macOS, wl-paste on Wayland, or xclip on X11.
When clipboard support is unavailable, type/paste a target in the form or use
the note picker. Path/URL type is inferred from the target, retaining the
existing @node:/path and note:ID conventions. Bookmark creation does not require
the path or remote node to be online. L continues to open existing links;
it does not create them.
