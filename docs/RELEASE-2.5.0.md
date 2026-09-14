# Future Crash + LOOK 2.5.0 — Capability platform

Versions:

- Future Crash + LOOK: 2.5.0
- LOOK: 4.5.0
- Future Crash: 1.1.10

## Vision

If the selected Ollama model advertises `vision`, LO can send image bytes with the normal chat request.

```text
lk vision screenshot.png "what is wrong here?"
lo what is in ./photo.jpg
```

Explicit local image paths are attached automatically in LO. A non-vision model reports that vision is unavailable rather than pretending to inspect the image.

## Optional local image generation

ComfyUI is treated as an optional service edge:

```text
lk comfy
lk comfy discover
lk comfy host http://HOST:8188
lk comfy workflow ~/workflows/look-image-api.json
lk comfy output ~/Pictures/LOOK
lk comfy preview on
lk generate "a winter street in Astoria, watercolor"
```

LOOK deliberately does not bundle or auto-download a giant checkpoint. `discover` searches standard Comfy locations and reports existing model files so older installations can be reused.

The configured workflow must be API-format JSON. LOOK substitutes:

```text
__PROMPT__
__NEGATIVE__
__SEED__
```

Generated image files are copied from Comfy's output API into LOOK's configured output folder and can be auto-previewed through the desktop bridge.

## Persistent scheduler

The resident `look_ai.py` service now owns delayed and recurring work:

```text
lk schedule
lk schedule in 30m summarize the project status
lk schedule every 2h check the local service health
lk schedule daily 08:00 give me a morning system report
lk schedule pause ID
lk schedule resume ID
lk schedule remove ID
lk schedule run ID
```

Schedules persist under LOOK state. When due, they become ordinary LO background jobs, so they reuse the existing job queue, access profile, workspace, event receipts, and foreground-priority rules.

Future Crash can use this scheduler as shared infrastructure in a later behavioral pass instead of growing a separate timing system.

## Settings / Doctor

`lk settings` now includes:

- Vision input
- Image generation / Comfy
- Scheduler

`lk doctor` reports the same capability state.

## Installation policy

Ollama remains the only core AI dependency. ComfyUI and image checkpoints are optional. The installer surfaces `lk comfy discover` but does not silently install/download large media models.
