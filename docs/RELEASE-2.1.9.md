# Future Crash + LOOK 2.1.9 — Ollama keep-alive compatibility

Versions:

- Future Crash + LOOK: 2.1.9
- LOOK: 4.1.9
- Future Crash: 1.1.8

2.1.8 introduced permanent model residency but encoded the value as a JSON string:

```json
"keep_alive": "-1"
```

Some Ollama builds reject that request with HTTP 400.

2.1.9 sends the API's numeric permanent-residency value:

```json
"keep_alive": -1
```

Everything else from 2.1.8 is unchanged.
