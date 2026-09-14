# Future Crash + LOOK 2.7.5

Future Crash now shares LOOK's Ollama-host truth.

Precedence:

```text
explicit `future-crash --ollama URL`
→ LOOK selected Ollama host
→ localhost:11434 fallback
```

This fixes `ORACLE LINK OFFLINE` on client machines where LO already talks successfully to the remote 3090.
