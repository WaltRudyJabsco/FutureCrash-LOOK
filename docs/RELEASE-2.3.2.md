# Future Crash + LOOK 2.3.2 — Native command authority

Versions:

- Future Crash + LOOK: 2.3.2
- LOOK: 4.3.2
- Future Crash: 1.1.10

## POWER command execution

Models no longer negotiate command permission in conversation.

The model proposes `run_command`. LOOK then owns the policy and any user interaction.

Known read-only inspections run immediately:

```text
ollama --version
git --version
python3 --version
ollama list
ollama ps
git status
nvidia-smi
pwd
whoami
uname ...
```

Unknown or potentially mutating commands use the native prompt:

```text
command › brew upgrade ollama
[y] once · [s] allow command this session · Enter/Esc cancel ›
```

A session grant applies only to that exact normalized command.

Shell composition, redirection, and destructive forms are never classified as safe inspection merely because they contain flags.

## No terminal-input competition

`run_command` subprocesses receive DEVNULL stdin. A background command therefore cannot accidentally steal input from LO's conversational terminal and appear to hang while waiting for input.

## Agent execution repair

Some models can identify the right command in reasoning but emit prose such as:

```text
I cannot check that here. Run `ollama --version`.
```

In POWER/UNSAFE, LOOK recognizes only a known-safe inspection in that situation, executes it once at the host layer, feeds the receipt back to the model, and asks for the final answer.

This is deliberately narrow. Unknown or mutating commands are never auto-extracted from prose.

## Thinking renderer

Compact thinking previously contained double-escaped terminal sequences:

```text
\r\033[2K
```

They are now actual control characters, restoring the intended rolling three-line compact display across Qwen and GPT-OSS-style thinking streams.

## Zsh natural language

`lo` is now wrapped with Zsh `nocorrect`, so prompts such as:

```text
lo what version ollama are we running
```

are passed to LO verbatim instead of prompting to replace `version` with a local `VERSION` filename.

## Model benchmark

`lk ollama test` now separates:

- **TOOLS** — controlled tool-schema judgment (3 tests)
- **AGENT** — whether a natural inspection request actually produces the appropriate tool call
- **EXACT** — deterministic response test
- TTFT / generation rate / declared capabilities

This prevents a 3/3 tool score from hiding an agent-execution weakness.
