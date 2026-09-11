# FUTURE CRASH + LOOK

**A local-first AI terminal environment for macOS and Linux.**

![Future Crash terminal](FC_screenshots/Normal.png)

Future Crash is the place you inhabit. **LOOK is the machinery underneath it.**

Future Crash gives a local language model a playful terminal front end. LOOK gives the terminal underneath it a compact language for navigation, files, machine inspection, Ollama, remote models, memory, learned skills, and controlled agentic work.

They started as separate projects. They now install and live as one system.

---

## Install

Installation happens in Terminal, but it is intentionally simple.

### 1. Download and unzip the release

Open Terminal. Type `cd ` — including the space — then drag the unzipped `future-crash-look-1.3.0` folder into the Terminal window and press Return.

Or navigate there normally:

```sh
cd ~/Downloads/future-crash-look-1.3.0
```

### 2. Give the installer permission to run

```sh
chmod +x install.sh
```

`chmod +x` simply marks the installer as executable. You normally do this once for a downloaded release.

### 3. Run it

```sh
./install.sh
```

The installer sets up Future Crash + LOOK, the shell integration, LOOK's command-line tools, documentation, and the optional terminal experience. It may also offer supporting software such as Tailscale or Ollama when they are not already present.

When it finishes:

```sh
exec zsh
future-crash
```

That is the front door.

![Future Crash after install](FC_screenshots/Normal.png)

The installer is rerunnable. A newer release updates the files the project owns; the same release reconciles them. Version-aware installers refuse to overwrite a newer release unless you deliberately use `--force-downgrade`.

---

## The idea in thirty seconds

There are three pieces:

```text
Future Crash   the experience
      ↓
LOOK           the terminal language and tools
      ↓
LO             the working local/remote AI
      ↓
Unix + Ollama  ordinary files, processes, models, network
```

You can live almost entirely in Future Crash, drop into LOOK when you want the underlying machine, or use LO directly when you want the AI without the Future Crash front end.

![Future Crash interface](FC_screenshots/Normal_3.png)

### Future Crash

Launch it with:

```sh
future-crash
```

or the shorter aliases:

```sh
fc
rst
```

Future Crash is conversational and ambient: observations, fortunes, system context, AI conversation, and the sense that the terminal itself has a personality.

Press `Esc` to expose the shell underneath. Type:

```sh
exit
```

to return to the same Future Crash session.

Nested Future Crash sessions are blocked by default so you do not accidentally end up six shells deep.

![Future Crash view](FC_screenshots/Error_2.png)

### LOOK

LOOK is the practical layer underneath Future Crash:

```sh
lk
```

It handles navigation, fuzzy finding, filtering, file inspection, system information, Ollama hosts and models, settings, memory, skills, and other small pieces of the machine.

A few useful starting points:

```sh
l
lr
lz
f
lk machine
lk doctor
lk settings
```

![LOOK file filter](FC_screenshots/LOOK_Shell_filter_find.png)

### LO

LO is LOOK's direct AI interface:

```sh
lo
```

It is conversation-first. File tools are available, but LO does not search the workspace merely because a tool exists. Casual conversation stays conversation; file and system tools come into play when the request actually calls for them.

```sh
lo
lo search
lo --conservative
lo --workspace
lo --power
lo --unsafe
```

![LOOK AI](FC_screenshots/LOOK_AI.png)

Future Crash and LO share the same selected Ollama model and host.

---

## First five minutes

After installation:

```sh
future-crash
```

Explore it for a moment. Press `Esc` to reveal the shell, then try:

```sh
lk
l
lk machine
lo
```

Inside LO, ask something conversational. Then ask it to inspect a file in the current folder. The point is that the same interface can move from ordinary conversation to real local work without pretending those are the same permission.

If you want to see what LO remembers:

```sh
lk memory
```

If you want to see what LO has learned about *doing its job*:

```sh
lk skills
```

![Future Crash / LOOK transition](FC_screenshots/Normal_2.png)

---

## AI setup

Future Crash + LOOK does not bundle a language model. It works with **Ollama**.

### Local model

If Ollama is installed on the same machine, pull any model appropriate for the hardware. For example:

```sh
ollama pull qwen3:8b
```

Then inspect or select models with:

```sh
lk ollama models
```

A lighter machine can use a smaller model. A workstation with more memory can use a much larger one.

### Remote model

The interface and the model do not have to run on the same computer.

A laptop can run Future Crash + LOOK while a desktop workstation runs Ollama:

```text
MacBook / Linux laptop
  ├── Future Crash
  └── LOOK / LO
         │
      Tailscale
         │
GPU workstation
  └── Ollama
```

Manage saved hosts with:

```sh
lk ollama host
```

Once a host is selected, Future Crash and LO inherit it automatically.

![Future Crash machine context](FC_screenshots/PNC.png)

### Web search

Ollama web search uses an Ollama API key. Configure it once:

```sh
lk ollama key
```

Check the configuration without exposing the key:

```sh
lk ollama key status
```

Web search is optional. LOOK's normal terminal features do not depend on it.

---

## Permission levels

LO separates **intelligence** from **permission**.

| Profile | What LO can do |
| --- | --- |
| **Conservative** | Read/search and reason; no writes |
| **Workspace** | Read and intentionally edit inside the starting workspace |
| **Power** | Workspace tools plus shell commands, confirmed individually |
| **Unsafe** | Unrestricted shell commands with the current user's privileges |

Workspace is the normal working mode. Unsafe is intentionally named.

Change the persistent profile from:

```sh
lk settings
```

or choose a one-session override:

```sh
lo --conservative
lo --workspace
lo --power
lo --unsafe
```

---

## Memory: small, selective, forgetful

LO does not dump a giant transcript into every prompt.

It keeps a bounded pool of candidate memories and only exposes a small working set to the model. Candidate memories have importance values, decay when they stop mattering, and strengthen when they genuinely prove useful.

```sh
lk memory
```

The design is deliberately simple:

```text
conversation
   ↓
candidate memories
   ↓
decay / reinforcement
   ↓
small working context
   ↓
durable patterns
   ↓
long-term summary
```

Explicit requests such as “remember this long term” can promote information directly into the long-term summary. The summary is not sacred or append-only; it periodically rewrites itself under a fixed size budget so stale, redundant, superseded, or low-value details can disappear.

Memory is stored in human-readable JSON and carries a **schema version**, so future LOOK releases can migrate the data format without treating the contents of your memory as an application version.

![LOOK doctor](FC_screenshots/LOOK_Shell_doctor.png)

---

## Skills: LO's accumulated craft

Memory is about **you**. Skills are about **how LO works**.

LO ships with reviewed bundled skills such as:

- inspect before modifying;
- prefer surgical changes over rewrites;
- preserve unrelated behavior;
- test changes when practical;
- treat user-owned shell configuration conservatively.

LO can also learn generalized techniques from successful work and place them in the `## Learned` section of `skills.md`.

```sh
lk skills
```

You can inspect and edit the file directly, or use:

```sh
lk skills add "Inspect the existing configuration before changing it"
lk skills forget "configuration"
lk skills clear-learned
```

### Skills have their own version

The application and the craft pack are intentionally separate concepts:

```text
Future Crash + LOOK   application release
memory schema         data-format version
skills schema         skills-file format
bundled skills pack   reviewed craft version
```

Check the installed craft pack:

```sh
lk skills version
```

Update the bundled section from the current release while preserving everything LO learned locally:

```sh
lk skills update
```

You can also merge another compatible skills pack:

```sh
lk skills update /path/to/skills.md
```

That means the program can eventually stabilize while the reviewed assistant craft continues to improve independently.

---

## Media controls

LOOK also exposes a tiny transport layer for music that is already playing:

```sh
lk media
lk media toggle
lk media next
lk media prev
lk media stop
```

On macOS, LOOK currently controls running **Music** or **Spotify** through their system scripting interfaces. On Linux it uses the standard **MPRIS** ecosystem through `playerctl`.

`lk media` reports the active supported player and track where available. The public interface stays the same even though the platform adapters underneath are different.

---

## Command completion

LOOK teaches Zsh its grammar.

Try:

```text
lk <Tab>
lk ollama <Tab>
lk ollama host <Tab>
lk memory <Tab>
lk skills <Tab>
lk media <Tab>
```

Saved Ollama host names are completed dynamically.

LO completes only its structural options and host selectors. After that, the command line is natural-language input rather than a giant command tree.

---

## The command map

You do not need to memorize this. Start with `future-crash`, `lk`, and `lo`.

| Command | Purpose |
| --- | --- |
| `future-crash` / `fc` / `rst` | Launch Future Crash |
| `lk` | LOOK command center |
| `lo` | Direct AI conversation |
| `l` | LOOK around / navigate |
| `lr` | Recent ordering |
| `lz` | Size-oriented view |
| `f` | Find under home |
| `lk machine` | Machine/system view |
| `lk doctor` | Diagnose the environment |
| `lk settings` | Unified settings |
| `lk ollama models` | Inspect/select models |
| `lk ollama host` | Inspect/select hosts |
| `lk ollama key` | Configure web-search key |
| `lk memory` | Inspect user memory |
| `lk skills` | Inspect assistant craft |
| `lk skills version` | Show skills schema/pack version |
| `lk skills update` | Refresh Bundled craft, preserve Learned |
| `lk media` | Show media state |
| `lk media toggle` | Play/pause |
| `lk media next` / `prev` | Next/previous track |

For the complete LOOK vocabulary:

```sh
lk help
man lk
```

---

## The terminal experience

Future Crash + LOOK runs in an ordinary Zsh terminal.

The reference visual stack is:

| macOS | Linux |
| --- | --- |
| iTerm2 | Kitty |
| Zsh | Zsh |
| Powerlevel10k | Powerlevel10k |
| MesloLGS NF | MesloLGS NF |

The installer can offer/check the pieces it can safely manage. Declining them does not disable the core project.

> **Portable by default. Gorgeous when equipped.**

![LOOK home](FC_screenshots/LOOK_home.png)

---

## Interactive typing

LO's `you ›` prompt uses readline/libedit when available, so normal terminal editing works:

- Left / Right arrows move within the line.
- Up / Down arrows recall input history.
- Home / End work where supported.
- Backspace/delete behave normally.

At the Zsh prompt, `lo` is a `noglob` alias, so characters such as `?`, `*`, and brackets can be used in one-shot prompts without turning into filename globs:

```sh
lo Do you know the band The Police?
```

Unmatched shell quotes are still parsed by Zsh before LO can see them. For unrestricted prose, simply enter interactive LO first:

```sh
lo
```

---

## Where it lives

The project uses ordinary Unix-style locations:

```text
~/.local/share/look/                  LOOK code + state
~/.local/share/future-crash/          Future Crash
~/.local/bin/lk                       LOOK launcher
~/.local/bin/future-crash             Future Crash launcher
~/.config/look/look.zsh               managed shell vocabulary
~/.config/look/completions/           Zsh completion definitions
~/.zsh_secrets                        user secrets
```

Your `~/.zshrc` remains your file. The installer backs it up and adds a small marked source hook rather than replacing it.

---

## Updating and version safety

This release establishes the following baseline:

| Layer | Version |
| --- | ---: |
| Future Crash + LOOK | **1.3.0** |
| LOOK | **3.6.0** |
| Future Crash | **1.0.0** |
| Memory schema | **1** |
| Skills schema | **1** |
| Bundled skills pack | **1** |

To update from a newer release directory:

```sh
./install.sh
```

The installer records product/component versions in:

```text
~/.local/share/look/install_manifest.json
```

A version-aware installer refuses to overwrite a newer unified release. A deliberate rollback remains possible:

```sh
./install.sh --force-downgrade
```

Historical installers that predate this guard cannot be made version-aware retroactively.

---

## Uninstall

From a release directory:

```sh
./install.sh --uninstall
```

or from an installed system:

```sh
lk uninstall
```

The uninstall removes files the project knows it owns. It does not casually remove unrelated Homebrew packages, Ollama, Tailscale, models, personal memory, or secrets.

![Future Crash interface](FC_screenshots/Error.png)

---

## Why Future Crash + LOOK are one project

Separate installers eventually became artificial.

Future Crash depended on the same model selection, remote-host logic, terminal behavior, memory, and shell environment that LOOK already managed. The unified project keeps the modules separate internally while treating distribution honestly:

```text
Future Crash   experience / personality
LOOK           terminal language / machine tools
LO             AI conversation / agency
Ollama         local or remote inference
Unix           files, processes, shell, network
```

One repository. One installer. One shell integration. One AI configuration.

The code remains modular because **one product does not require one giant program**.

---

## Design principles

**Local first.** Files and state remain ordinary local computing primitives.

**Keyboard first.** Fast paths should become muscle memory.

**Boring underneath.** Files are files. Commands are commands. Configuration has visible locations.

**Progressive power.** Reading a file and running an unrestricted shell command are not the same permission.

**Small memory.** Remember more than you think about at once; forget what stops mattering.

**Accumulated craft.** The model supplies raw intelligence. LOOK supplies learned technique.

**Remote without becoming cloud software.** A laptop can use your own workstation over a private network.

**Readable machinery.** The project is Python, shell, Markdown, and JSON—not an opaque application bundle.

---

## Platform and status

Future Crash + LOOK is designed around **macOS and Linux**, Zsh, Python 3, and ordinary Unix tools.

LOOK itself is lightweight. Local-AI hardware requirements are mostly determined by the model you choose. Remote Ollama support exists precisely so the machine running the interface does not have to be the machine doing the inference.

This remains an enthusiast-built terminal environment with intentionally powerful modes. Keep normal backups and understand Power/Unsafe before enabling them.

The point is not to make the terminal disappear.

**The point is to see what the terminal becomes when it can think.**
