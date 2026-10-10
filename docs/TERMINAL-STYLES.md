# Terminal styles and editor movement

Future Crash + LOOK ships a shared Kitty profile in terminal/kitty.conf.
The green phosphor palette, transparency/blur, cursor trail, and Mac/Linux
keyboard mappings are part of that profile, activated by ./install.sh --kitty.
Personal overrides belong in kitty-local.conf.

The optional appearance command provides one local entry point on each node:

    lk terminal
    lk terminal launch paper
    lk terminal theme paper
    lk terminal theme neon
    lk terminal theme slate
    lk terminal customize
    lk terminal customize paper
    lk terminal theme custom
    lk terminal theme reset

In an interactive terminal, lk terminal opens the palette picker: arrows move,
Enter applies, E fine-tunes the highlighted preset into Custom, and Escape cancels.
In a pipe or script it still prints the palette list.

The palettes are Neon (the existing green LOOK colors), Paper (MercuryWriter's
warm white #f6f1e7 and dark ink #201e1a), and Slate (quiet charcoal).
Paper uses saturated navy, red, green, and violet inks, including LOOK’s
explicit RGB directory headings and Markdown file labels. Selection uses a yellow
highlighter with dark text. Prompt panels for OS/time and Git use lighter neutral,
green, and gold backgrounds so dark prompt text stays readable. LOOK ink accents
use their own indexed colors rather than borrowing those prompt backgrounds.

Launch opens a separate Kitty window with palette overrides. It does not change
saved preferences or recolor other windows. Theme saves an appearance-only
look-theme.conf include and asks the current Kitty process to reload when it can
identify that process. Otherwise press Ctrl-Shift-F5 or reopen Kitty. The first
change backs up kitty.conf; later appearance changes retain previous theme files.
Reset empties the appearance layer, restoring the underlying configuration,
including a custom opacity such as 0.72. It keeps the saved custom palette
and does not reset Notes, shell settings, or Powerlevel10k. Neon preserves opacity/blur from the
underlying profile; Paper and Slate request opaque backgrounds without blur or
cursor trails. kitty-local.conf loads last and still takes precedence.

This command requires an existing Kitty configuration for persistent changes.
It does not replace fonts, shell settings, or keyboard mappings. Ordinary product
installs and Fabric runtime updates do not switch terminal preferences. Choose a
palette separately on each node; it does not change every computer at once.
iTerm settings remain independent. LOOK coordinates its explicit RGB colors with
Paper and Custom. Other programs that emit their own RGB colors may retain them.
After changing palettes, close and reopen an existing LOOK view to refresh its
text colors. Apply Paper again after updating to refresh its indexed ink colors.
No Powerlevel10k configuration wizard is needed.

Custom is one editable style, saved locally in look-custom.json beside kitty.conf.
Run lk terminal customize: arrows select a role, Enter opens the color choices,
and Enter confirms a choice. S saves and applies; Escape returns from choices or
cancels without changing the active theme. The samples show a directory heading, Markdown file label, red/green ink,
and a selected file. You can choose the paper/background, text ink, accent,
muted text, green/red pen inks, active-tab color, and selection/highlighter color. Low-contrast text colors must be
changed before saving; tab and selection text automatically use black or white.
Run lk terminal customize paper (or neon/slate) to start from that preset; saving
creates your one Custom style and leaves the built-in preset unchanged. For a
dark background, choose lighter text inks. Previous saved files are backed
up. Use lk terminal theme custom to return to this style after another palette,
or lk terminal launch custom to open it in a separate window.

In the Notes quick editor:
- Option/Alt-Left/Right jumps by Unicode word/punctuation groups.
- Ctrl-Left/Right is an alternative where the terminal reports those keys.
- Option/Alt-Up/Down jumps between paragraphs separated by blank lines.
- Shift-Up/Down and Page Up/Down keep page movement.
- Shift-Left/Right keeps note start/end; Home/End keeps line start/end.
- The link dialog also supports word movement in target and label fields.

The shared Kitty profile passes Option/Alt and Shift-arrow combinations through
to applications. On other terminals, modifier-key transmission may need to be
enabled in that terminal's settings. Existing list/preview shortcuts are unchanged.

Kitty's official configuration reference documents include files, reload,
and indexed-color customization:
https://sw.kovidgoyal.net/kitty/conf/
