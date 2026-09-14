# Future Crash + LOOK 2.5.2

Versions:

- Future Crash + LOOK: 2.5.2
- LOOK: 4.5.2
- Future Crash: 1.1.10

## Persistent UNSAFE consent

The permission model now distinguishes a saved preference from an ad-hoc escalation.

```text
lk ollama access unsafe
→ strong confirmation once
→ saves UNSAFE as the user's chosen profile

lo ...
→ starts UNSAFE directly
→ no repeated session confirmation

lo --unsafe
→ explicit temporary escalation
→ asks for confirmation for that session
```

UNSAFE continues to authorize filesystem paths outside the starting workspace as well as shell commands. WORKSPACE and POWER retain their bounded/grant behavior.
