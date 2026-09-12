# Future Crash + LOOK 2.0.3

## Deterministic directory inspection

LO no longer needs to list a directory into context and count entries itself.

The read-only `inspect_directory` tool returns exact, bounded statistics:

```text
path
recursive
files
directories
symlinks
other
total_entries
file_bytes
scanned_entries
truncated
limit
elapsed_ms
```

LO is instructed to prefer this tool for exact file/folder counts and directory-stat questions.

## Natural feedback as weak supervision

Ordinary conversation can now help LO improve without a special training UI.

Clear feedback such as “great job,” “that worked,” “that didn’t work,” or “you made that up” triggers a detached background review of the immediately preceding interaction.

The reviewer may produce exactly one result:

- `NONE` — nothing reusable was learned.
- `NEW` — a new generalized operational skill.
- `REINFORCE` — an existing learned skill clearly contributed to success.
- `WEAKEN` — an existing skill clearly contributed to failure.
- `CORRECT` — a reusable corrective lesson.

Praise/criticism itself is never stored as a skill.

`skills.md` remains readable/editable. Reinforcement state is stored in `skill_state.json`, which travels with the portable profile.

Use:

```text
lk skills state
```

to inspect confidence and positive/negative hits.

LOOK is 4.0.3. Future Crash remains 1.1.7.
