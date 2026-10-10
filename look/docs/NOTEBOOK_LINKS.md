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
