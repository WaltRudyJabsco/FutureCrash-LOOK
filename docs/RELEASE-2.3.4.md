# Future Crash + LOOK 2.3.4

Versions:

- Future Crash + LOOK: 2.3.4
- LOOK: 4.3.4
- Future Crash: 1.1.10

## Fix

`lk ollama test` previously used the generic resident-model chooser. If `qwen3:30b` was already resident, selecting `deepseek-r1:32b` or `qwen3:8b` in `lk ollama models` could still benchmark `qwen3:30b`.

Single-model testing now means exactly:

```text
LOOK-selected model
→ verify installed on active host
→ benchmark that model
```

Resident state affects warm/cold timing, but no longer changes which model is tested.

`lk ollama test --all` continues to test all enabled installed models.
