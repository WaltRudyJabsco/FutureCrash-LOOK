# Future Crash + LOOK 2.7.4

A surgical distributed-Comfy fix.

On a client machine:

```text
configured Comfy?
  ↓ offline
discover Tailscale peers :8188
  ↓ reachable
save remote host → ready
```

Only a Linux machine with an NVIDIA GPU is offered the managed local Comfy bootstrap.

`lk generate` and LO's image-generation tool use the same self-healing discovery before failing, so a newly installed laptop can find a shared 3090 Comfy service without installing ComfyUI or diffusion models locally.

On the GPU host:

```text
lk share
```

On a client:

```text
lk comfy discover
lk comfy
```
