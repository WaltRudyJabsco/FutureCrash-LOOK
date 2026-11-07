# Gypsy Astronaut TV

The personal animation channel keeps the original GIFs supplied by Gypsy
Astronaut's public Tumblr API, with post links and tags. It does not invent
higher-resolution URLs or bypass the site's HTML access restrictions.

- `lk gypsy` or `lk tv gypsy`: native desktop TV.
- `/gypsy` in Signal or Albert: fullscreen-capable browser TV.
- `[Gypsy Astronaut](look:gypsy)`: a Notes launcher.
- `lk gypsy status`: archive progress.
- `lk gypsy sync`: start/resume downloading on the configured owner.
- `lk gypsy cancel`: stop after the current network request.
- Choose **Gypsy Astronaut** in `lk saver` or the music visualizer picker.
- `lk lk gypsy` or `/lock gypsy`: the existing PIN curtain with animations.
- **Afterimage** is the new ambient luminous-ring visual, available in both pickers.

TV controls: left/right changes animations, Space holds/resumes the slideshow,
`f` toggles fullscreen, Escape leaves fullscreen (then closes native TV).
Hold keeps the current GIF looping; it does not freeze its animation.
Native screensavers allocate separate lanes to attached displays, avoiding
repeats across those displays while enough cached GIFs are available. Each lane reshuffles on subsequent laps and starts with its own random timing. Browser
curtains use independent shuffle bags and timing; separate browser sessions may
occasionally coincide.

## Storage and setup

`~/.config/look/animations.json` holds user-specific configuration:

```json
{"node":"local","root":"~/Media/animations/gypsyastronaut"}
```

On a remote viewer set `node` to the trusted archive owner's Fabric name. On the
owner use `local`; optionally set `require_mount` to its mounted media volume
so an absent drive cannot redirect downloads onto the system disk. Downloading
is explicit and preserves originals. Failed files are retried by a later sync.
The job pauses below 2 GiB free. Individual downloads are bounded at 64 MiB.

Native viewers keep a disposable offline cache of up to 128 GIFs / 512 MiB.
The owner retains the full archive. The browser streams from its authenticated
Signal/Albert host; it is not a separate offline browser installation.

`python -m animation_backup` uses the existing authorized FabBack repository,
backs up a consistent catalog and original GIFs, and restores/checks a sample.
An owner-local timer can call this module; no new backup destination is enrolled.
