# Future Crash + LOOK 2.8.0

This pass makes LOOK's shell language more predictable and adds two deterministic utility edges.

## Shell grammar

`f` is the optional personal Future Crash shortcut. `fc` remains Zsh's native history builtin permanently.

`l -` follows the familiar `cd -` convention and immediately opens LOOK in the destination.

`lmk` now owns a small explicit option grammar. Unknown flags fail safely. `--` ends option parsing so filenames beginning with a dash remain possible.

## Pattern selection

`lk match 'future-crash-*' v` returns the highest natural/version-like match.
Use `t` for modification time, `n` for name, and `--all` to list the ranked set.

Quote wildcard patterns when you want LOOK—not the shell—to perform matching.

## Translation

`lk translate` is a deterministic edge for a configured LibreTranslate-compatible API. It deliberately does not pretend an LLM answer is an authoritative translation result.

Configure a local/self-hosted service with:

    lk translate host http://HOST:5000

Then:

    lk translate es "Good morning"
    lk translate en fr "Where is the station?"

The provider remains optional; LOOK works normally without it.
