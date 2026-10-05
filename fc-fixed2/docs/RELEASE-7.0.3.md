# Future Crash + LOOK 7.0.3 — JEV TREES

The first reusable JEV decision tree moves small, obvious language judgments into deterministic core logic.

## Command tree

```text
RUN/LAUNCH imperative
  ├─ strip semantic suffixes: AGAIN / CURRENT TERMINAL / NEW TERMINAL
  ├─ one payload token → command
  ├─ multiple payload tokens + resolvable executable head → command + argv
  └─ otherwise → cognition
```

JEV never executes commands. LOOK supplies host facts, rechecks the active access profile and risk policy, performs the action, and records the receipt.

Observed regressions frozen in this release:

- `run asciiquarium in a new terminal` → command `asciiquarium`, new-terminal presentation.
- `run asciiquarium again` → command `asciiquarium`, retry semantics; `again` is not argv.
