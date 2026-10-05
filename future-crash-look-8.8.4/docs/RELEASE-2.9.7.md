# Future Crash + LOOK 2.9.7

## Actual architecture, not intended architecture

Runtime testing showed that a request succeeded from `~` but failed from `FutureCrash-LOOK`. The audit found two routing leaks: discovery was still modeled partly as a cwd-relative path operation, and the raw shell-search guard contained an incorrectly escaped regular expression.

`search_files` now defaults to a semantic `personal` scope that is independent of cwd. The filesystem dispatcher receives the active access profile explicitly. Both the normal command path and the prose-repair path block shell filesystem discovery, keeping one canonical discovery edge.

Use `lk architecture-audit` to print the critical routing contract and `lk locator-test` to exercise the locator without an LLM.
