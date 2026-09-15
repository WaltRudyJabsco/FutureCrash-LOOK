# Future Crash + LOOK 2.8.7

One model contract:

```text
INSTALLED  exists on Ollama host
LOADED     currently occupies Ollama memory
ACTIVE     shared LOOK/Future Crash default
OVERRIDE   explicit process-specific --model
```

`lk models` selection sets ACTIVE and preloads it. LO, Oracle, Ask, Workstation, and background AI use ACTIVE by default. A loaded model never silently becomes active.

Future Crash shows `model · shared` normally and `model · override` only when deliberately launched with `--model`.
