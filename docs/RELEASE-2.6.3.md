# Future Crash + LOOK 2.6.3

A surgical Comfy readiness fix.

`lk comfy` no longer merely echoes a workflow string. It validates the file with the same resolver used by `lk generate`.

When LOOK's packaged starter exists, an empty or stale workflow pointer repairs automatically:

```text
workflow     SDXL starter · ready
             ~/.local/share/look/workflows/sdxl-api.json
```

Manual recovery is now:

```text
lk comfy repair
```

No knowledge of API-format workflow JSON paths is required for the managed SDXL starter.

Managed Comfy is also included in local model inventory, including nested checkpoint/model-family subdirectories.
