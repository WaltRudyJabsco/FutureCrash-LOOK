# LOOK Shell

**Keep Unix. Lose some syntax.**

LOOK is an opinionated, human-readable interaction layer for a Unix workstation. It does not replace the shell, Finder, Git, Neovim, Tailscale, or Ollama. It gives the things you already use a small shared language built around intent.

The mental model is deliberately physical:

```text
l        look around here
f        find the thing I remember
lk X     tell me what I need to know about X
G        take me there
B        put this file in my clipboard
Y        give me its path
lo       talk about this workspace
lh       come home
Esc      back out
```

LOOK began as a better `ls`. It became a semantic control layer for the terminal: **find something, understand it, act on it, and keep moving.**

## Five minutes with LOOK

Look around the current directory:

```sh
l
```

Type ordinary fragments to filter. `Tab` marks things; `A` toggles all current matches: mark them all, or clear them all when they are already marked. With no marks, actions apply to the highlighted object. With marks, they apply to the marked set.

```text
Enter    open / enter folder
Tab      mark or unmark
A        mark / clear all matches
B        copy the actual file(s) to the desktop clipboard
Y        copy path(s) as text
C        copy to another filesystem location
M        move
R        remove
E        edit
O        open with
G        leave LOOK and make this the shell's real directory
Esc      clear / back
q        quit
```

On macOS, `B` uses native clipboard file objects for documents and folders and image data for a single common image, so the result can be pasted into Finder-, Mail-, chat-, and image-aware applications. `Y` is intentionally different: it copies the pathname as text.

Now find something anywhere under your home directory:

```sh
f
```

Start typing whatever you remember: part of a filename, project, directory, or phrase. LOOK uses `fd` + `fzf`, skips common cache/project junk, and hands the result back to the same LOOK action language. It does **not** immediately launch the result.

When you already know the next action is editing, `fznv` remains the direct fuzzy-to-Neovim path.

## `lk` means “look at this”

The inspection grammar is intentionally conservative:

```text
lk .                 what is here?
lk mercury_server.py inspect this file
lk python3           what is this command?
lk 8080              what owns this port?
lk process ollama    find this process
lk git               what is happening in this repository?
lk run               what can I do in this directory?
lk machine           what machine am I on?
lk disk              how is storage doing?
lk net               how am I connected?
lk tailscale         what is the tailnet doing?
lk ollama            what is Ollama doing?
lk env               what environment am I in?
lk why python        which python am I actually calling?
```

Existing paths are paths. Port-range numbers are ports. Executable names are commands. Process matching is conservative. Inspection is the default; mutation is explicit.

`lk doctor` checks the LOOK environment. `lk config`, `lk secrets`, `lk version`, and `lk help` expose the installation without revealing secret contents.

## Files without becoming a file manager

The short views are muscle-memory front doors:

```text
l / ls    smart interactive view
ll        details
ld        directories
lf        files
lt        tree
lr        recent
lz        sizes
zll WORD  zoxide jump + look
cdl WORD  zoxide jump + details
```

Bare `ls` uses LOOK. `ls` with arguments remains ordinary Unix `ls`, and `command ls` is always available.

LOOK keeps navigation in Zsh and presentation in Python. Entering folders inside LOOK does not silently change the parent shell. `G` is the explicit handoff: **go here for real**.

Escape is state-sensitive and consistent: clear a filter, cancel selection state, move back through LOOK's in-session browse history, then stay put at the starting point. `q` exits.

## Safe file actions

LOOK's local mutations are explicit and journaled:

```text
lcp [PATH]    copy
lmv [PATH]    move
lrm [PATH]    remove with confirmation
lmk PATH      make directory path
lscp [PATH]   scp (remote; outside local undo)
lk undo       undo the last LOOK local filesystem transaction
```

Multi-item browser operations are one undo transaction. Deletes go through LOOK's private trash so they can be restored when safe. Copy undo verifies the copied object has not changed; move undo refuses to overwrite a newly occupied original path.

The design rule is simple: **dangerous operations should be obvious, and mistakes should be recoverable when LOOK can prove recovery is safe.**

## Preview what you found

LOOK previews text and code directly. If `chafa` is present, common images render inside the terminal. PDFs can render page one when a local rasterizer is available; `pdftotext` also lets LOOK and LO extract text from text-bearing PDFs.

These are capabilities, not alternate interfaces. A missing preview helper degrades gracefully to text or metadata.

## LO: local AI with hands, not a shell

If Ollama is installed:

```text
lo
lo explain this project
lo search current Qwen3 tool support
lk ollama
lk ollama models
lk ollama test
lk ollama test --all
```

LO can inspect and modify the current workspace through bounded LOOK tools: list, read, search, write, copy, move, remove, and make directories. In the default `workspace` profile, arbitrary shell execution remains unavailable. `power` and `unsafe` explicitly add shell-command capability, with different confirmation behavior. The model handles meaning; LOOK controls which capabilities are exposed.

LO keeps five recent compressed exchange notes plus a rolling long summary in a local mode-0600 state file. Memory compression happens in a detached background worker so the prompt returns immediately.

When `OLLAMA_API_KEY` is present, `lo search` can use Ollama web search. Secrets stay in `~/.zsh_secrets`; LOOK reports their status but never prints their contents.

## Remote terminal

LOOK ships a small `webterm()` helper:

```sh
webterm
```

With `ttyd` and Tailscale available, it starts a writable Zsh terminal on local port 7681 and exposes it through Tailscale Serve on HTTPS port 8443. The point is not to invent remote administration; it is to make your own terminal available to your own devices with a tiny, memorable gesture.

## Install from GitHub

The dependable route is deliberately simple.

### From a Release

1. Open the repository's **Releases** page.
2. Download the LOOK ZIP attached to the newest release.
3. Unzip it.
4. In Terminal, `cd` into the folder you just unzipped.
5. Run:

```sh
chmod +x install.sh
./install.sh
```

GitHub downloads do not always preserve executable permissions, which is why the `chmod` step is included.

### From the green Code button

You can also use **Code → Download ZIP** on the repository page. Unzip it, enter the resulting folder (GitHub will usually name it something like `look-shell-main`), then run the same two commands:

```sh
chmod +x install.sh
./install.sh
```

The installer uses its own location as the source directory, so the checkout folder can have any name. You do **not** need to rename it.

### Terminal-only download

If you want to use `curl`, copy the actual ZIP URL shown by GitHub for the release you want rather than relying on a guessed asset name. For example:

```sh
curl -L "PASTE-THE-RELEASE-ZIP-URL-HERE" -o look-shell.zip
unzip look-shell.zip
cd <the-folder-that-was-created>
chmod +x install.sh
./install.sh
```

LOOK intentionally does not document a magic `/releases/latest/download/look-shell.zip` URL because that only works when the release maintainer has uploaded an asset with exactly that filename.


## Canonical command reference

`lk help` is the authoritative live command/key glossary. The README explains the system and workflows; `man lk` is the compact Unix reference; `docs/COMMANDS.md` is the repository-friendly command sheet.

`lk settings` is the unified interactive surface for persistent AI/remote controls, but it is only a front end over the existing `lk ollama ...` commands and state. The direct commands remain supported and scriptable.

## Unified settings

LOOK's command grammar remains the source of truth, but persistent AI/remote state can also be managed from one place:

```sh
lk settings
```

The panel shows the current access profile, Ollama host, preferred model, web-search key status, and Ollama tailnet-share state. Use arrows or `j`/`k` through `fzf`, press Enter to change/open a setting, and Esc to return.

The settings panel is deliberately only a UI over the existing commands and state files. Nothing new is stored just for the panel:

```text
Access profile       ↔ lk ollama access
Ollama host          ↔ lk ollama host
Preferred model      ↔ lk ollama models
Web search key       ↔ lk ollama key
Tailnet share        ↔ lk ollama share
```

The direct commands remain fully supported for scripts, muscle memory, and troubleshooting.

## LO access profiles

LOOK keeps **model intelligence** separate from **machine authority**. A model running on another Ollama host still acts on the computer where LOOK is running.

The existing bounded workspace behavior remains the default:

```text
conservative   read/search the starting workspace + web; no mutation
workspace      LOOK's bounded file tools inside the starting workspace
power          workspace tools + shell commands; confirm every command
unsafe         unrestricted shell commands for the session
```

Use a profile temporarily:

```sh
lo --conservative
lo --workspace
lo --power
lo --unsafe
```

Profiles compose with remote inference:

```sh
lo --power @workstation
lo @workstation --power
```

In both cases the model runs on `workstation`, while commands execute on the computer where you typed `lo`.

Set the persistent default with:

```sh
lk ollama access
lk ollama access power
lk ollama access workspace
```

`power` prints each proposed command and asks before executing it. `unsafe` asks once when the LO session begins, then permits shell commands without per-command confirmation. Commands run with the current user's privileges and environment. LOOK does not silently become root, though an explicitly chosen command may invoke normal system authentication such as `sudo`.

The shell tool lets LO test code, run builds, install packages, use Git, inspect processes, perform system cleanup, and operate command-line software instead of only editing files. For ordinary file work, LOOK's structured workspace tools remain preferable because they retain bounded, purpose-specific behavior.


### Thinking and answer presentation

Thinking-capable models may return reasoning in Ollama's structured `message.thinking` field or through model-template `<think>...</think>` markup. LOOK handles both, including the Qwen compatibility case where the opening tag is stripped but a trailing `</think>` remains. Reasoning stays visible as a muted/italic `thinking ›` section before the normal high-contrast `lo ›` answer. Tool activity (`file ›`, `command ›`, `search ›`) remains visually separate as well.

### Memory and accumulated craft

LO's persistent intelligence remains deliberately inspectable:

```text
~/.local/share/look/core.md
~/.local/share/look/skills.md
~/.local/share/look/ollama_memory.json
```

`core.md` defines stable LO behavior. `skills.md` contains reusable assistant craft. `ollama_memory.json` contains this user's long-term summary and bounded dynamic memories.

```sh
lk memory
lk memory add "Prefer surgical modifications" --importance 90
lk memory forget "old topic"
lk forget "old topic"
lk memory clear
lk memory clear-summary
lk memory prune
lk clear-memory
lk skills
```

LO may retain up to 20 candidate memories while offering at most eight to immediate prompt attention. Memories have importance from 0–100 and unused candidates decay during maintenance. **Retrieval is not reinforcement.** A fresh installation begins with blank user memory but reviewed bundled skills.

## Ollama anywhere: local, remote, or tailnet

LOOK 3.1 separates the `lo` interface from the machine doing the inference. Local Ollama remains the default and nothing remote is required.

```sh
lk ollama host
```

lists the current host, saved host profiles, and reachable Ollama servers LOOK discovers on your Tailscale peers. Tailscale device hostnames become the profile names automatically.

Select one persistently:

```sh
lk ollama host workstation
```

or use it for just one chat session:

```sh
lo @workstation
lo @workstation explain this project
```

Return to the current machine with `lk ollama host local`.

A host can also be saved explicitly:

```sh
lk ollama host workstation https://workstation.example.ts.net
```

Remove a saved profile with `lk ollama host forget workstation`.

To share the current machine's localhost Ollama only inside your tailnet:

```sh
lk ollama share
```

This uses Tailscale Serve in the background through a localhost-only LOOK proxy that preserves Ollama’s host protection. If Tailscale requires root/operator permission for Serve changes, LOOK keeps the proxy ready and prints the exact one-time `sudo tailscale serve --bg 11435` handoff. `lk ollama share status` shows the Serve state and `lk ollama share off` turns off this Ollama share.

Tailscale is optional. Without it, local Ollama and manually saved host URLs continue to work normally. LOOK still speaks the Ollama API only; 3.1 does not add provider-specific OpenAI or Anthropic adapters.

### Optional Ollama web search

If you use `lo`, a free Ollama account/API key enables its built-in web search. After installation:

```sh
lk ollama key
```

The key is stored privately in `~/.zsh_secrets`. `lk ollama key status` checks whether one is configured without revealing it.

## Shell configuration: integrate, don't replace

LOOK keeps `~/.zshrc` user-owned. On install/update it:

1. makes a timestamped backup of the current `~/.zshrc`;
2. installs LOOK's shell fragment at `~/.config/look/look.zsh`;
3. adds one clearly marked source hook to the existing `.zshrc`;
4. leaves every other line untouched.

```zsh
# >>> LOOK Shell >>>
[[ -f "$HOME/.config/look/look.zsh" ]] && source "$HOME/.config/look/look.zsh"
# <<< LOOK Shell <<<
```

Re-running the installer refreshes only LOOK's fragment and normalizes the hook to one copy. `lk uninstall` removes that hook and fragment; legacy installs that replaced `.zshrc` still use the recorded backup restoration path.

## The opinionated installer

A fresh LOOK machine should behave like the LOOK we actually use.

```sh
chmod +x install.sh
./install.sh --dry-run
./install.sh
exec zsh
lk doctor
```

The **LOOK workstation** is installed automatically through Homebrew/Linuxbrew:

```text
zsh · python · git · zoxide · fzf · fd · neovim · bat
fortune · cowsay · fastfetch · chafa · poppler · ttyd · lsof
```

LOOK also installs Oh My Zsh, Powerlevel10k, zsh-autosuggestions, and zsh-syntax-highlighting. It backs up an existing `.zshrc`, preserves `.zsh_secrets`, installs itself under `~/.local/share/look`, and puts `lk` in `~/.local/bin`.

Two larger choices are offered separately:

- **Remote:** Tailscale is offered with a default of Yes because `webterm()` is already part of LOOK. Authentication into a tailnet remains yours.
- **AI:** Ollama is offered with a default of No. LOOK works without AI; `lo` becomes available when Ollama does.

For unattended installs, `--yes` accepts both optional offers. `--no-optional` installs only the workstation.

### Uninstall cleanly

LOOK has an exit door from the beginning:

```sh
lk uninstall
```

The uninstaller removes LOOK itself and restores the pre-LOOK `.zshrc` recorded by the installer. Before restoring it, LOOK preserves the current `.zshrc` as a timestamped `~/.zshrc.look-uninstalled.*` file so any edits made while using LOOK are still recoverable. `~/.zsh_secrets` is always preserved.

The installer also records exactly which Homebrew/Linuxbrew packages and shell add-on directories **it** created. During uninstall, LOOK offers to remove only those recorded dependencies. Anything that already existed before LOOK is left alone. Older LOOK installations without an ownership manifest err on the safe side and leave dependencies installed.

LOOK never automatically removes Homebrew/Linuxbrew itself.

### The Neovim joke, fixed

LOOK installs Neovim because a capable terminal editor should be there when `E` or `fznv` needs one. The first time LOOK itself opens Neovim, it teaches the one command Unix folklore assumes you already know:

```text
LOOK is opening Neovim.
To leave: Esc  :q  Enter
You'll only be told this once.
```

Then it never says it again.

## A little terminal personality

`lh` is LOOK's home screen: current directory, Git state, Ollama state, and a small fortune/cowsay ritual. `rs` remains the reset ritual. `rb` reloads Zsh.

LOOK 3 uses terminal-native truecolor when available and falls back to ANSI. The 2.2 interaction grammar is the compatibility constitution:

```sh
LOOK_CLASSIC=1 lk
LOOK_CLASSIC=1 l
LOOK_CLASSIC=1 lo
```

Presentation may evolve. Muscle memory should not.

## Reference

LOOK keeps documentation in three layers:

1. **README** — the mental model, installation, and feature guide.
2. **`lk help` / `commands`** — the complete in-terminal command and key glossary.
3. **Contextual footers** — only the keys that matter in the state you are currently using.

There is intentionally no separate installed man/TLDR tree to drift out of sync. This section and `lk help` are the canonical reference.

### Complete command map

```text
LOOK / VIEWS
  lk [THING]                 inspect a path, command, port, or process
  lk detail [PATH]           detailed filesystem view
  lk dirs [PATH]             directories
  lk files [PATH]            files
  lk tree [PATH]             tree
  lk recent [PATH]           newest first
  lk size [PATH]             size-oriented
  lk run [PATH]              project/run inspection
  lk project [PATH]          alias of lk run

SYSTEM INSPECTION
  lk up | ports | services   listening services
  lk port NUMBER             one port
  lk process TERM | proc     process search
  lk processes | procs       interactive process list; Y copies PID
  lk pid NUMBER              one PID
  lk git [PATH]              Git state
  lk machine                 machine capabilities
  lk gpu                     GPU information
  lk disk                    disk usage
  lk net                     interactive addresses; Y copies IP
  lk tailscale               tailnet status
  lk env                     environment
  lk path                    PATH diagnostics
  lk why COMMAND             command resolution

OLLAMA / LO
  lo [ASK]                   local/default-host chat
  lo search [ASK]            chat with Ollama web search
  lo @HOST [ASK]             temporary host for one LO session
  lk o --no-start ...        do not auto-start missing local Ollama
  lk ollama                  Ollama and selected-host status
  lk ollama models           select/enable installed models
  lk ollama test             benchmark current model
  lk ollama test --all       compare enabled installed models
  lk ollama host             list saved/discovered hosts
  lk ollama host NAME        select persistent default
  lk ollama host local       return to localhost
  lk ollama host NAME URL    save and select an explicit endpoint
  lk ollama host forget NAME remove a saved remote profile
  lk ollama share            expose local Ollama through Tailscale Serve
  lk ollama share status     Serve + localhost rewrite-proxy status
  lk ollama share off        stop the Ollama tailnet share
  lk ollama key              securely write OLLAMA_API_KEY
  lk ollama key status       report key configuration without revealing it

MAINTENANCE
  lk home                    LOOK home
  lk settings                 unified interactive settings
  lk doctor                  environment check
  lk config                  installed/state paths
  lk secrets                 secret-file status, never contents
  lk undo                    undo last safe local filesystem transaction
  lk uninstall               uninstall LOOK; optionally remove owned deps
  lk version                 version
  lk help                    complete in-terminal glossary
```

### Shell vocabulary

```text
l / ls      smart interactive view       ll       details
ld          directories                  lf       files
lt          tree                         lr       recent
lz          sizes                        zll WORD jump + look
cdl WORD    jump + details               f        find anywhere → LOOK
fznv        fuzzy find → Neovim          lh       LOOK home
lcp         assisted copy                lmv      assisted move
lscp        assisted scp                 lrm      assisted remove
lmk PATH    make directory path          mkd DIR  make + enter
lo          Ollama chat                  webterm  terminal over Tailscale
rs          reset ritual                 rb       reload Zsh
commands    same complete glossary as lk help
```

`ll`, `ld`, `lf`, `lt`, `lr`, and `lz` resolve directory arguments exactly like `l`: an existing path wins; otherwise LOOK asks zoxide for the best matching directory. Thus `lr labs` can open the recent view for a previously visited `labs` directory from anywhere.

Bare `ls` is LOOK; `ls` with arguments and `command ls` reach ordinary Unix `ls`.

### Interactive file language

```text
Type        filter immediately
j/k/↑/↓     move selection; J/K/L/; also provide home-row directions
Tab         mark / unmark
A           mark all current matches / clear all marked matches
Enter       open file / enter folder
E           edit
O           open with
C           copy to filesystem destination
M           move
R           remove
B           copy actual file object(s) to desktop clipboard
Y           copy absolute path(s) as text
P           print absolute path and exit
G           leave LOOK and make this the shell's real directory
Esc         clear / back / cancel
q           quit
```

In a file card, `S` adds SCP. Long LOOK/help views use `Space`/`b` for paging, `j`/`k` or arrows for lines, `g`/`G` for the ends, and `q`/`Esc` to leave.

`CHANGELOG.md` records release history. The command map above is deliberately redundant with `lk help`: the README explains the system; the terminal glossary is the fast operational reference.

## Platform and philosophy

LOOK targets macOS and Linux with Zsh. The renderer and inspector are Python standard-library programs; external tools are used only where they provide a real capability.

The core rules:

- Keep the common path obvious.
- Inspect before mutating.
- Keep Unix underneath.
- Prefer gestures over syntax trivia.
- Make state visible.
- Let optional capabilities degrade gracefully.
- Undo what can be undone safely.
- Do not turn the terminal into a dashboard.
- Do not make the user remember machinery that LOOK can remember for them.

**Keep Unix. Lose some syntax.**

## Zsh completion

The unified installer installs `_lk` and `_lo` completion definitions under `~/.config/look/completions`.

`lk` completion is context-sensitive for Ollama, memory, skills, system commands, paths, and saved remote host names. `lo` completes only its command/options layer before yielding to natural-language input.

## Media transport

LOOK exposes a small cross-platform transport surface:

```sh
lk media
lk media toggle
lk media next
lk media prev
lk media stop
```

macOS controls an already-open Music or Spotify instance through AppleScript. Linux uses MPRIS through `playerctl`. Every successful media transport command reports the resulting state/track immediately. Fast aliases: `mm` (toggle), `mn` (next), `mp` (previous).

## Versioned intelligence

User memory and assistant craft are portable state, not application binaries.

- `ollama_memory.json` carries `schema_version: 1`.
- `skills.md` carries `schema: 1` and `bundled-version: 1`.
- The Bundled skills section is release-owned.
- The Learned section is local and preserved when Bundled craft is updated.

```sh
lk skills version
lk skills update
lk skills update /path/to/skills.md
```

`lk skills update` replaces compatible Bundled craft while preserving the local Learned section.

## Smart make

`lmk` is LOOK's unified creation command:

```sh
lmk notes.md        # file
lmk project/        # directory + enter
lmk -f Makefile     # explicit file
lmk -d project      # explicit directory + enter
```

Names with a suffix and dotfiles imply file intent. A trailing slash implies directory intent. Extensionless names are prompted as `[d]irectory` or `[f]ile`.

File and directory creation are journaled and available to `lk undo`. Undo refuses to remove a created file after it has changed or a created directory after it contains anything.

`mkd DIR` remains as a compatibility wrapper around `lmk -d DIR`.


## Personality and thinking

`lk personality [lo|robot|max|philosopher]` selects an inspectable Markdown personality pack.

`lk thinking [light|adaptive|deep]` controls actual reasoning effort on Ollama models that advertise thinking support. Light uses no deliberate thinking and an 800-token output ceiling; adaptive uses up to 1400 tokens and escalates deliberate thinking for structurally complex work; deep enables thinking with a 2000-token ceiling. LO uses an 8192-token working context with bounded recent history.

`lk think-display [compact|full|quiet]` controls visible reasoning presentation. Compact is the default rolling live view.

These settings are independent of LO's access/capability profile. Personality never grants tools or permissions.

## Selected paths → LO

Inside LOOK's interactive filer, filter and mark files with the existing selection controls, then press `L` to open LO with those paths as explicit context. If nothing is marked, the highlighted path is used.

This is a path handoff, not a bulk content injection. LO stays within its bounded workspace and reads only what the task needs.


## Filer keys

Use `j/k` (or `J/K`) and ↑/↓ for vertical movement. `L` is reserved for the selected-path LO handoff.


## Parent navigation

Press `<` (Shift-,) in ordinary browse mode to move to the filesystem parent. This is separate from Escape/back history. Filter-entry mode continues to treat `>` as normal text.


## Persistent working set

Filer marks persist while navigating between directories. `Tab` toggles an item, `A` toggles current matches, and `X` clears the set. Actions operate on the full set. The status is green when all selections are local and amber with `N / H HERE` when selected paths exist elsewhere.


## Completion and global find

Copy/move destination prompts support Tab path completion. Shell file-action helpers use normal repeated Zsh filesystem completion for every operand.

`f` and `fznv` now use LOOK's own global finder presentation over a fast `$HOME` catalog rather than exposing stock fzf directly.

## Temporal memory contract

Recent exchanges and semantic memories carry age information. Semantic candidates store creation and last-reinforcement timestamps.

Memory is historical context, not queued intent. LO must never resume an older request solely because it appears in recent or semantic memory.

## Background jobs and events

`lo bg REQUEST` queues a one-shot LO job in LOOK state. Completion emits an event, and the Zsh prompt hook displays pending events when the user returns to a normal prompt.

`lk jobs` and `lk events` expose the durable state. This is the message-passing boundary for future shell/Future Crash integration.


## LOOK 4 / Profile architecture

`lk profile` manages portable identity independently from the installed program. Use `backup`, `export`, and `restore` for durable migration.

`lk feedback` controls finite motion and optional local synthesized sound. `lk sound` toggles sound quickly. Feedback is suppressed outside a TTY.

See `../docs/STATE-ARCHITECTURE.md`, `../docs/PROFILE.md`, and `../docs/FEEDBACK.md`.
