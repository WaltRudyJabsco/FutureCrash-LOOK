# Future Crash + LOOK 2.6.0 — GPU workstation bootstrap

Versions:

- Future Crash + LOOK: 2.6.0
- LOOK: 4.6.0
- Future Crash: 1.1.10

## Where Comfy lives

ComfyUI belongs on the machine doing GPU inference. On a LOOK setup with a Linux RTX tower and lighter clients, install Comfy on the GPU tower.

The client does not need a local Comfy install merely to use a remote Comfy service.

## Installer behavior

On Linux with an NVIDIA GPU, `install.sh` now offers:

```text
LOOK GENERATIVE MEDIA
  ✓ NVIDIA GPU · ...
  ComfyUI enables local image generation; old model folders can be reused without copying.
  Set up local ComfyUI image generation on this GPU? [Y/n]
```

If accepted, LOOK:

1. scans for previous ComfyUI / A1111 / Forge installs and model folders;
2. reports large checkpoint files found on HOME and common mounted-drive paths;
3. installs or updates a fresh managed ComfyUI codebase;
4. creates an isolated Python virtual environment;
5. installs current NVIDIA PyTorch + Comfy requirements;
6. enables the built-in ComfyUI Manager dependencies;
7. optionally wires old model libraries into `extra_model_paths.yaml`;
8. offers an explicit starter-model menu;
9. writes a managed launcher and LOOK Comfy configuration.

Managed code lives under:

```text
~/.local/share/look/services/comfyui/
```

Large model libraries can remain on other disks.

## Discovery

```text
lk comfy discover
```

scans:

```text
$HOME
/mnt
/media/$USER
/run/media/$USER
```

at bounded depth.

It recognizes:

- ComfyUI roots (`main.py`)
- A1111 / Forge roots
- checkpoints
- diffusion_models / unet folders
- common `.safetensors`, `.ckpt`, `.pt`, `.pth`, and `.gguf` model files

Discovery is read-only.

## Reusing old models

When structural old installs are found, LOOK can generate:

```text
ComfyUI/extra_model_paths.yaml
```

so the new managed Comfy can see the old weights without copying them.

This follows ComfyUI's native external-model-path mechanism.

## Starter models

The bootstrap offers:

```text
[1] Reuse existing models only
[2] SDXL 1.0 base · ready-to-run LOOK starter · ~6.9 GB
[3] FLUX.1 Schnell FP8 · modern fast checkpoint · ~17.2 GB
[4] Both
[5] Skip
```

Downloads are explicit, resumable, and verified with known SHA-256 hashes.

### SDXL starter

SDXL is used as the guaranteed ready-to-run compatibility starter because LOOK ships a simple API-format workflow for it.

Installing SDXL configures:

```text
~/.local/share/look/workflows/sdxl-api.json
```

so after Comfy starts:

```text
lk generate "an old harbor town in winter, watercolor"
```

has a complete model + workflow path.

### FLUX.1 Schnell FP8

The optional Comfy-Org single-file FP8 checkpoint is suitable for a 24 GB-class GPU and is offered as the more modern fast model option. LOOK does not force the SDXL workflow onto FLUX; select/export an appropriate FLUX API workflow before making it the automation workflow.

## Managed service

```text
lk comfy
lk comfy start
lk comfy stop
lk comfy restart
lk comfy discover
lk comfy bootstrap
```

The launcher is:

```text
~/.local/bin/look-comfy
```

and binds Comfy to `127.0.0.1:8188` by default.

`lk generate` attempts to start this managed local service automatically if the configured localhost Comfy endpoint is offline.

## Manager

Current manual ComfyUI installations include the new Manager in core; LOOK installs its manager requirements and starts Comfy with `--enable-manager`.

## Safety / ownership

LOOK never silently downloads a 7–24 GB model. Model downloads are a separate, visible user choice.

Uninstalling LOOK should be treated separately from deleting image models; model libraries may predate LOOK or live on shared/mounted storage.
