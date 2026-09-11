# LOOK migration notes

LOOK is designed to be upgraded in place. The installer preserves user-owned shell configuration, LOOK state, secrets, and existing data unless a feature explicitly requires migration.

## Upgrading to 3.3

LOOK 3.3 adds `lk settings` as a unified interactive view over the existing access-profile, Ollama-host, model, key, and tailnet-share controls. It introduces no second configuration store; all direct commands remain valid.

Thinking-capable model output is now visually separated from the final answer. Capability and confirmation semantics are unchanged.

## Upgrading to 3.2

### LO access profiles

LOOK 3.2 adds four capability profiles:

- `conservative` — read/search only
- `workspace` — bounded LOOK file tools; this remains the default
- `power` — workspace tools plus shell commands, confirmed one command at a time
- `unsafe` — unrestricted shell commands after one explicit session-entry confirmation

Existing installs therefore retain the same authority they had before 3.2 until the user deliberately selects another profile.

Use:

```sh
lk ollama access
lk ollama access power
lk ollama access workspace
```

or override one session with:

```sh
lo --conservative
lo --workspace
lo --power
lo --unsafe
```

Remote inference and local authority remain separate. `lo @HOST --power` runs the model on `HOST`, but commands execute on the computer where LOOK itself is running.

## Upgrading from pre-3.1.6 installs

Older LOOK installers could replace `~/.zshrc` wholesale. Current LOOK does not.

Modern installs:

1. back up the current `~/.zshrc`;
2. install LOOK's shell fragment at `~/.config/look/look.zsh`;
3. add one marked source block to the user's existing `.zshrc`;
4. leave the rest of the file untouched.

`lk uninstall` understands both layouts: modern installs remove only the marked hook and LOOK fragment; legacy installs can restore the recorded pre-LOOK backup.

## Remote Ollama

LOOK 3.1 introduced named Ollama hosts and optional Tailscale discovery.

```sh
lk ollama host
lk ollama host NAME
lo @NAME
```

`lk ollama share` uses a localhost rewrite proxy plus Tailscale Serve so Ollama can remain bound to localhost while remote LOOK clients reach it privately over the tailnet.

If Tailscale Serve requires operator/root permission, LOOK keeps the local proxy alive and prints the exact privileged handoff instead of invoking `sudo` itself.

## Compatibility

The LOOK 2.2 interaction grammar remains the behavioral compatibility baseline. Upgrades should preserve:

- `l`, `ll`, `ld`, `lf`, `lt`, `lr`, `lz`
- filter/selection controls
- clipboard/path actions
- `G` directory handoff
- undo behavior
- LO workspace tools
- remote Ollama host routing
- `xyzzy`

Presentation and capability layers may evolve, but established muscle memory should not silently change.
