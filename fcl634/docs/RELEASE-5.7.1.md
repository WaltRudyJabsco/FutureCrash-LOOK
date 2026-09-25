# Future Crash + LOOK 5.7.1 — Smart Resolver

5.7.1 preserves the complete 5.7.0 Fabric Content Search release and adds a shared deterministic filesystem resolver for `lk open`, `lk preview`, and `lk reveal`.

- Exact paths still win.
- A single unresolved argument may fall back to the local file catalog.
- Quoted phrases such as `lk open "labs folder"` use `folder`/`directory` as a type hint.
- Multiple unquoted arguments remain literal LK command grammar; LOOK does not silently turn the CLI into natural language.
- Ambiguous matches are shown rather than guessed.
- Directory candidates are inferred from indexed file parents, requiring no new catalog schema migration.

LO remains the conversational layer; LOOK resolves; LK executes.
