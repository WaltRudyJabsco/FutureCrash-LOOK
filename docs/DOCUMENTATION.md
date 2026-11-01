# Documentation maintenance

## Current application

The combined repository owns the Fabric, current LOOK, Future Crash, Signal,
Albert and the optional pinned Mercury companion. Standalone repositories and
the Alternate rewrite retain their own versions, installers and commands.
A feature documented in the combined app is not automatically available in a
standalone predecessor.

| Surface | Source of truth |
|---|---|
| LOOK command list and arguments | `look/lk`, executable help and `tools/command_reference.py` |
| Generated Markdown, JSON and man page | `python3 tools/command_reference.py` |
| Interactive shortcuts | Help/footer definitions in each actual UI |
| Mercury commands and Mini bindings | Mercury repository's `tools/command_reference.py` and `mercury_terminal.py` |
| Firmware and keyboard configuration | Each repository's committed keymap/configuration |

Run `python3 tools/command_reference.py --check` after a command change. It
checks generated files without overwriting them. New screenshots should use
fictional data and an isolated home directory; never expose real clipboard,
manuscript or private configuration contents.

## Installed manual

The full LOOK installer copies `look/lk.1` into the user man directory.
Managed runtime updates currently carry the Markdown and JSON references,
but do not replace installed man pages. After updating a trusted checkout:

```sh
mkdir -p "${XDG_DATA_HOME:-$HOME/.local/share}/man/man1"
cp look/lk.1 "${XDG_DATA_HOME:-$HOME/.local/share}/man/man1/lk.1"
man lk
```

For a source preview, use `man ./look/lk.1`. Mercury's repository supplies
`mercury.1` with its own installation instructions. The standalone Look-Shell
root manual belongs to that repository's root implementation; its nested older
snapshot remains historical.

## Repeat terminal captures

`tools/capture_terminal.py` runs a real program in a pseudo-terminal and renders
its ANSI output through pyte and Pillow. These are development dependencies,
not runtime dependencies. Install them in a temporary virtual environment.

```sh
python3 tools/capture_terminal.py --output /tmp/commands.png --cwd "$PWD" -- python3 look/lk commands
```

The default capture uses a temporary demo home, records dimensions in a JSON
receipt, and stops only its own child process group. Check the resulting image
before using it in a README. Keep receipts outside public screenshots because
command arguments may include local paths. Browser captures use the running
web app and fictional manuscripts.

## Repository map

- [MercuryWriter](https://github.com/WaltRudyJabsco/MercuryWriter): writing studio, browser and terminal editors.
- [FutureCrash](https://github.com/WaltRudyJabsco/FutureCrash): standalone Future Crash 1.1.12.
- [Look-Shell](https://github.com/WaltRudyJabsco/Look-Shell): root standalone LOOK 4.8.1; older nested snapshot preserved.
- [future_crash_oracle](https://github.com/WaltRudyJabsco/future_crash_oracle): several standalone Oracle prototypes.
- [FutureCrash-LOOK-Alternate](https://github.com/WaltRudyJabsco/FutureCrash-LOOK-Alternate): separate modular 4.0.0 rewrite.
- `zmk-config`, `5-col-view`, `corne-5-plus`: distinct ZMK configurations; inspect each manifest and hardware matrix.
- Private `configs` and `dotfiles`: workstation notes and Kanata profiles; contents remain private.
