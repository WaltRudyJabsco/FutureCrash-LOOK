# Future Crash + LOOK 2.6.2

A surgical Comfy polish release.

- Empty workflow settings no longer become `Path('.')`.
- `lk generate` now reports `No Comfy workflow configured` instead of an `Errno 21` directory error.
- `lk comfy discover` scans up to three levels beneath recognized checkpoint/diffusion-model roots, catching old model collections organized into family subdirectories.
- The existing working 3090 generation path is unchanged.
