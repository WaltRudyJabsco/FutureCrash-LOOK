# LOOK 2.0 State Architecture

## 1. Program

Versioned, replaceable distribution material.

Examples:

- `look/lk`
- `look/look_renderer.py`
- bundled `core.md`
- bundled `skills.md`
- bundled personalities
- installer/completions/docs

An upgrade may replace program files.

## 2. Profile

Portable user identity. Upgrades must not erase it.

Live roots:

- `~/.local/share/look/`
- selected portable preferences under `~/.config/look/`

Portable profile content:

- `ollama_memory.json`
- `lo_recent.json`
- `core.md`
- `skills.md`
- `skill_state.json` — reinforcement metadata for learned skills
- `personalities/`
- `lo_access`
- `lo_personality`
- `lo_thinking`
- `lo_think_display`
- `ollama_model`
- `~/.config/look/feedback.json`

The backup destination itself is machine policy and is not exported.

## 3. Machine

Valid on one machine or trust boundary, not portable identity.

Examples:

- `~/.zsh_secrets`
- Ollama/Tailscale host configuration
- local service exposure
- hardware availability
- environment/PATH

These are re-established on a new machine.

## 4. Runtime

Disposable transactional/process state.

Examples:

- undo journal and undo trash
- jobs/events
- memory worker queue and lock
- proxy PID
- generated feedback WAV cache

Runtime state is intentionally excluded from profile backups.

## Rule

**Program may be reinstalled. Runtime may be discarded. Machine state may be reconfigured. Profile is the user's durable LOOK.**
