# Future Crash + LOOK 2.3.1

Versions:

- Future Crash + LOOK: 2.3.1
- LOOK: 4.3.1
- Future Crash: 1.1.10

## Fix

LOOK 4.3.0 made long-term memory retrieval query-aware, but the initial message setup attempted:

```text
_memory_context(memory, prompt)
```

before `prompt` had been assigned.

4.3.1 uses a stable memory system-message slot. For every user turn:

```text
read current prompt
→ reload latest memory
→ retrieve relevant memory for this prompt
→ replace memory slot
→ run inference
```

This preserves query-aware retrieval without carrying obsolete memory snapshots forward in the conversation.
