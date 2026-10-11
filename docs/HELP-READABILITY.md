# Help readability audit

`lk help all` and `lk doc` use the same generated reference and pager.
Complete command forms and key combinations use bold terminal cyan; section
headings use bold terminal purple. Descriptions retain the default foreground.
These standard palette colors follow the terminal theme. Plain piped output
contains no added color. Text, spacing and headings also identify each role.

Up/Down (or j/k) moves one line. Shift-Up/Down and PgUp/PgDn move a page;
Left/Right and b/Space also move back/forward a page. Shift-Left/Right,
Home/End and g/G move to the beginning/end. Q, q and Escape close help.
Runnable notebook commands keep their existing return-to-note prompt.

## Shared shortcut surfaces reviewed

- Full reference: generated command rows were unindented, while the old color
  matcher expected indented glossary rows. Fixed in this update.
- Help pager: its separate decoder truncated modified arrow sequences. It now
  uses the same decoder as other LOOK selectors.
- Media selectors: use the shared file-browser action footer and preserve plain
  pipe output. Existing tests check wrapping without losing action labels.
- Notes editor/workspace: use `command_hints`, applied after wrapping/clipping.
  Its fixed pale cyan and dim descriptions merit a separate theme-contrast pass,
  especially on light backgrounds. Some long hints are clipped to terminal width;
  check narrower windows and prioritize essential editing shortcuts in that pass.

Future shortcut changes should keep keys distinct from descriptions, preserve
normal contrast for essential instructions, wrap without dropping actions, and
retain plain output when redirected. Verify both light and dark terminal themes.
