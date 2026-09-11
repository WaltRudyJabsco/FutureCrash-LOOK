# FUTURE CRASH + LOOK

**A local-first AI terminal environment for macOS and Linux.**

Future Crash is the place you inhabit. **LOOK is the machinery underneath it.**

Future Crash gives a local language model a playful, persistent terminal front end. LOOK turns the terminal underneath it into a fast keyboard-driven environment for navigation, files, system inspection, Ollama, web search, remote AI hosts, and controlled agentic work.

They began as separate projects. They now install and live as one system.

---

## Quick start

Unzip the release, open Terminal, enter the folder, and run:

```sh
chmod +x install.sh
./install.sh
```

When installation finishes:

```sh
exec zsh
future-crash
```

That's the front door.

You can also launch it with:

```sh
rst
```

or:

```sh
fc
```

LOOK is always underneath:

```sh
lk
```

The installer is designed to be rerunnable. Updating the project should update the files it owns rather than spraying duplicate PATH entries and aliases through your shell configuration.

---

## What is this?

There are three layers.

### Future Crash — the front end

Future Crash is the ambient AI terminal: conversation, observations, fortunes, system context, web-aware local AI, and a deliberately old-computer/new-computer personality.

It is meant to feel less like opening an AI website and more like having an intelligent machine sitting at the command line.

```text
future-crash
rst
fc
```

### LOOK — the terminal underneath

LOOK is a keyboard-first shell environment built around the idea that ordinary terminal work should require less ceremony.

It handles navigation, fuzzy finding, file inspection, filtering, opening and editing files, machine information, Ollama configuration, remote hosts, and the command vocabulary shared by the environment.

```text
lk
l
lr
lz
f
```

### LO — the working AI

LO is LOOK's direct Ollama interface. It can use local or remote models, web search, workspace tools, and graduated capability profiles.

```text
lo
lk settings
```

Future Crash and LO share LOOK's selected Ollama host and model. Configure the machine once; both interfaces use it.

---

## What you get

A normal install gives you the complete Future Crash + LOOK codebase:

- **Future Crash** — the interactive AI front end.
- **LOOK** — navigation, filtering, file and system tools.
- **LO** — direct Ollama chat and agentic work.
- **Fuzzy navigation** — move around without typing perfect paths.
- **Terminal file workflow** — inspect, filter, open, edit, search.
- **Machine awareness** — useful system information through LOOK.
- **Ollama management** — models, hosts, status and configuration.
- **Remote Ollama support** — use a stronger computer over Tailscale.
- **Web-search integration** — when an Ollama web-search key is configured.
- **Capability profiles** — Conservative, Workspace, Power and Unsafe.
- **Unified settings** — AI host, model and access configuration in one place.

The environment remains useful without every optional component. LOOK itself does not require a local language model simply to navigate files or inspect a machine.

---

## The command map

You do not need to memorize this to begin. Start with `future-crash`, `lk`, and `lo`.

| Command | Purpose |
| --- | --- |
| `future-crash` | Launch Future Crash |
| `rst` / `fc` | Short Future Crash launchers |
| `lk` | LOOK command center |
| `lo` | Talk directly to the configured Ollama model |
| `l` | LOOK around / navigate |
| `lr` | LOOK with recent ordering |
| `lz` | LOOK with size ordering |
| `f` | Find under home |
| `lk settings` | Unified settings |
| `lk machine` | Machine/system view |
| `lk doctor` | Diagnose the installation |
| `lk ollama models` | Inspect/select Ollama models |
| `lk ollama host` | Inspect/select Ollama hosts |
| `lk ollama key` | Configure the Ollama web-search key |
| `lk ollama key status` | Check web-key configuration |
| `lk ollama serve status` | Inspect Ollama/Tailscale serving state |

LOOK's interactive filter footer exposes the contextual keys for opening, editing and acting on results; the terminal itself is the documentation while you work.

For the complete LOOK vocabulary, see the bundled LOOK documentation and:

```sh
man lk
```

---

## AI: local, remote, or both

The environment is deliberately not tied to one topology.

### Local

Run Ollama on the same machine:

```text
Mac/Linux
  ├── Future Crash
  ├── LOOK
  └── Ollama + model
```

### Remote

Run the interface on a laptop and the model on a stronger machine:

```text
MacBook
  ├── Future Crash
  └── LOOK
         │
      Tailscale
         │
3090 workstation
  └── Ollama + larger model
```

Select the remote host in LOOK and Future Crash inherits it:

```sh
lk ollama host
future-crash
```

The front end stays on the machine in front of you; the expensive inference can happen somewhere else.

---

## Models

Ollama and model files are third-party components, not bundled into this small repository.

A modest machine can start with a smaller model; a stronger machine can use a larger one. The project does not require one particular model forever—the selected LOOK model is shared with Future Crash.

Check what is available with:

```sh
lk ollama models
```

If Ollama is not installed, the installer can guide the optional AI setup rather than making Ollama a hidden prerequisite for the rest of the environment.

---

## Web search

Future Crash and LO can use Ollama's web-search service when an Ollama API key is configured.

Configure it with:

```sh
lk ollama key
```

Check it with:

```sh
lk ollama key status
```

The key is kept outside the project source in the user's secrets configuration. Do not commit API keys to GitHub.

Web search is optional. Local inference and LOOK's normal terminal features do not depend on it.

---

## Capability profiles

LO deliberately separates *intelligence* from *permission*.

### Conservative

Read-oriented. Useful when you want the model to inspect and reason without changing the workspace.

### Workspace

Allows intentional file creation and editing inside the working area. This is the normal coding/writing-agent mode.

### Power

Adds shell-command capability, but commands requiring execution are surfaced for confirmation.

### Unsafe

Unrestricted shell commands run with the current user's privileges without per-command confirmation.

Unsafe is intentionally named. It is for machines and sessions where you explicitly want that power—not a default that quietly bypasses the operating system.

Choose and inspect these from:

```sh
lk settings
```

---

## Installation philosophy

The project uses boring Unix locations rather than hiding itself inside Homebrew or copying scripts loosely into `$HOME`.

```text
~/.local/share/look/                  LOOK code + state
~/.local/share/future-crash/          Future Crash
~/.local/bin/lk                       LOOK launcher
~/.local/bin/future-crash             Future Crash launcher
~/.config/look/look.zsh               managed shell vocabulary
~/.zsh_secrets                        user secrets
```

`~/.zshrc` remains **your file**.

The installer backs it up and adds a small marked source hook for the managed LOOK/Future Crash shell fragment. Project aliases and functions live in that fragment instead of replacing the user's shell configuration.

`~/.local/bin` is added to `PATH` when needed.

---

## What the installer may offer

The repository contains Future Crash and LOOK. Some capabilities rely on ordinary external software.

Depending on the machine and the choices you make during installation, setup may offer or check for things such as:

- Python 3
- Homebrew on macOS
- Ollama
- a local Ollama model
- Tailscale for remote/private networking
- the command-line utilities LOOK uses for richer previews and workflows

Optional infrastructure remains optional. The goal is not to pretend that Homebrew, Ollama, an AI model, a web account and Tailscale are all one application.

The project installs the environment; third-party services remain recognizable third-party services.

---

## A first five minutes

After installation:

```sh
exec zsh
future-crash
```

Explore Future Crash. Then drop into the underlying terminal and try:

```sh
lk
l
lk machine
lo
```

If you have more than one Ollama machine:

```sh
lk ollama host
```

If you want to inspect or change what LO is allowed to do:

```sh
lk settings
```

The system is designed to reveal depth gradually. You can use Future Crash without first learning the whole LOOK vocabulary.

---

## Why merge Future Crash and LOOK?

Originally they were separate projects.

That became increasingly artificial. Future Crash depended on the same Ollama configuration, terminal behavior, remote-host logic and shell environment that LOOK was already managing. Separate installers meant duplicated state, duplicated documentation, alias collisions and two projects pretending not to be one system.

The merged project keeps the code modular but makes distribution honest:

```text
Future Crash   experience / personality
      │
      ▼
LOOK           terminal language / tools
      │
      ▼
Ollama         local or remote intelligence
      │
      ▼
Unix           files, processes, shell, machine
```

One repository. One installer. One shell integration. One AI configuration. Two deliberately different interfaces.

---

## Design principles

**Local first.** Your terminal and files remain ordinary local computing primitives.

**Keyboard first.** Fast paths matter. Commands should become muscle memory.

**Boring underneath.** Files are files. Commands are commands. Configuration has visible locations.

**Progressive power.** Reading a file and running an unrestricted shell command are not the same permission.

**Remote without becoming cloud software.** A laptop can use your own workstation over a private Tailscale network.

**AI as a layer, not the operating system.** If the model disappears, the underlying terminal should still make sense.

**Readable machinery.** The project is Python, shell and ordinary configuration rather than an opaque application bundle.

---

## Updating

The installer is intended to be idempotent. From a newer release directory, run:

```sh
./install.sh
```

It updates the project-owned installation while preserving user-owned secrets and shell configuration.

Before substantial changes, keeping normal backups of your home configuration is still sensible. This is a terminal environment with intentionally powerful modes.

---

## Uninstall

From the release directory:

```sh
./install.sh --uninstall
```

or from an installed system:

```sh
lk uninstall
```

The unified uninstall removes Future Crash + LOOK files owned by the environment.

It does **not** assume ownership of unrelated software or personal data. User secrets are preserved rather than casually deleted, and third-party software such as Homebrew, Ollama or Tailscale is not removed merely because this project can use it.

---

## Source tree

```text
future-crash-look/
├── install.sh
├── README.md
├── look/
│   ├── lk
│   ├── look_renderer.py
│   ├── zshrc
│   ├── lk.1
│   └── docs/
├── future-crash/
│   ├── future_crash.py
│   └── future-crash
└── docs/
    └── ARCHITECTURE.md
```

The boundary is intentional: **one product does not require one giant program**.

LOOK can evolve as the terminal/tool layer while Future Crash evolves as the experience layer.

---

## Platform

The project is designed around **macOS and Linux**, Zsh, Python 3 and ordinary Unix command-line tools.

Hardware requirements for LOOK itself are modest. Hardware requirements for local AI depend overwhelmingly on the model you choose. Remote Ollama support exists specifically so the computer running the interface does not have to be the computer doing the inference.

---

## Status

Future Crash + LOOK is an enthusiast-built terminal environment. It intentionally explores powerful local-agent behavior, including modes capable of modifying files and executing shell commands.

Expect sharp edges. Keep backups. Understand what Power and Unsafe mean before enabling them.

The point is not to make the terminal disappear.

The point is to see what the terminal becomes when it can think.
