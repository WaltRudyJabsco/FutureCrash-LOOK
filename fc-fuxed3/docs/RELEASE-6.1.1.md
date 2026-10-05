# 6.1.1 — Fabric Edge Repair

This maintenance release fixes Fabric-wide browser endpoint approval when the invoking machine is briefly served by an older resident node, clarifies why an unpaired Tailscale-discovered peer has no direct Tailcat route, and makes ComfyUI VRAM reclaimable without taking its web service offline.

`lk comfy unload` POSTs ComfyUI's `/free` request with model unload and memory release enabled. LOOK-generated images auto-unload by default; `lk comfy auto-unload off` preserves warm model residency when desired.

OpenJev installation remains unchanged in this release; capture any prerequisite warnings from a manual/server start so they can be normalized rather than guessed.
