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

Mac captures use the native `screencapture` tool, as Fabric Vision does, instead
of Qt's pixel-reading API. Qt still supplies the numbered picker and exact display
rectangles, then exits. The original terminal process performs the native capture,
matching the existing Vision permission context. Failed or uniform frames are rejected before saving or copying, leaving
the clipboard unchanged. Existing terminal capture authorization may already be
sufficient; no privacy-setting reset is needed. If macOS requests permission,
authorize the application it identifies in Screen & System Audio Recording.

## Camera photos

`lk photo` opens a local browser preview with a camera-source selector. Press
Start camera, allow the browser camera prompt, then Take photo. Built-in, USB
and Continuity cameras appear when the OS and browser expose them as cameras.
Only video is requested. Done stops the camera and closes the local capture
service. Sessions expire after 30 minutes.

Photos are saved under `~/Pictures/LOOK Photos` and added to LK Clip. The image
is also copied to the system clipboard when its image backend is available.
`--output-dir DIR` selects another destination. Captures fit the existing 3 MiB
clipboard attachment limit, with a maximum initial edge of 1920 pixels.
The capture page is served only on a random loopback port and uses a per-session
token plus same-origin checks for uploads. Camera permission and capture remain
explicit browser actions.

Signal and Albert's CAM button also saves a PNG copy to `Pictures/LOOK Photos`
on the computer hosting that web page and adds it to that host's LK Clip. The
photo remains attached to chat. A phone or Mac browser connected to the 3090
therefore saves that copy on the 3090. Normal opt-in clipboard publication makes
it available to other paired shelves. The capture feedback names the host and
saved path. Browser camera inputs can offer a camera or an image picker depending
on the platform. `lk photo` provides the explicit live-preview/source-picker UI.

### Printed QR tickets

In `lk photo`, choose Start camera, then Scan QR. Hold the ticket steady and keep
its full square visible. Photo decodes frames on this computer and shows the
recognized text or link. Open in browser opens a recognized HTTP/HTTPS link and
stops the camera. A Theater ticket goes directly to its movie admission page.
The scanner pauses after each recognition; Scan another resumes it. Photo capture
and saving continue to use Take photo as before.

The offline decoder is jsQR 1.4.0 by the jsQR contributors, licensed under Apache
2.0. Its source is https://github.com/cozmo/jsQR and its license ships alongside
`qr_decoder.js`. Camera frames used for scanning are not uploaded or saved.
