# Screenshots and recording

`lk shot` opens a local numbered monitor picker on Mac and X11. Click monitors
or toggle their numbers, press `a` for all, then Enter. Escape cancels. The
three-second countdown gives you time to arrange the scene; overlays disappear
before capture. No model, remote capture, or persistent recording service is used.

- `lk shot all` captures all connected displays after the countdown.
- `lk shot 2` captures display 2.
- `lk shot 1,3 --delay 5` captures selected displays after five seconds.
- `lk shot --save ~/Desktop/screen.png` also saves the screenshot; it never overwrites.
- `lk shot record` opens native recording controls on Mac/Spectacle, or shows GNOME’s native shortcut.
- `[Screenshot](look:shot)` adds the picker to a Note.

Multiple displays become one full-resolution PNG arranged side by side in display
number order, with black padding under shorter displays. The PNG is copied to the
system clipboard. LK Clip history can retain/share it when enabled and below its
3 MiB attachment limit. Larger screenshots still go to the system clipboard.

The picker uses the existing optional Saver Qt runtime (`lk saver setup`). Mac
may request Screen Recording permission for the terminal/runtime. Keyboard numbers
cover displays 1–9; additional monitors can be clicked.

On Wayland the compositor owns capture selection and permission. `lk shot` opens
the interactive desktop screenshot portal and copies its result. Screen numbers
are not accepted there; selection and timing use the desktop picker. This avoids
pretending that an arbitrary application can capture monitors behind the portal.

Recording uses the desktop's own start/stop, destination and selection controls.
GNOME does not expose a public recorder-launch method here, so the command directs
you to Print → video mode or the Screenshot button in Quick Settings.
LOOK does not yet provide synchronized multi-monitor video recording, audio mixing,
or a custom cross-platform recorder. OBS is optional for those advanced uses.

Mac captures now check Screen Recording authorization before reading pixels.
A denied capture can otherwise return a valid-sized solid desktop image. Such
uniform frames are rejected and leave the clipboard unchanged. If permission is
requested, enable the terminal/capture application identified by macOS in Privacy
& Security → Screen & System Audio Recording, restart it, then capture again.
