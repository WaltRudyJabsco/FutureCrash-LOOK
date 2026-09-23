# Signal Window 1.7.0

## 1.7.0 — explicit media endpoints

OUT is rendered as stable endpoint buttons. `This iPhone`/`This Device` is handled entirely by browser audio; Fabric nodes use node handoff. Cross-node playback streams source media through Fabric rather than adopting another machine's filesystem paths.


Signal is a browser body for LO/Fabric: conversation, lightweight visual expression, shared decisions, shared media state, browser audio endpoints, and camera/photo input.

## 1.6.0 — media endpoints

The chat composer is generic again: **OUT** appears only on the active media card. The chooser lists playback-ready Fabric nodes plus an ephemeral **This Device** endpoint; on iPhone Safari it is labeled **This iPhone**. Selecting the browser endpoint streams the current queue item through HTML audio, then stops the former node player only after browser playback starts.

Selecting a Fabric node while browser playback is active hands the source session to that node at the browser's current queue index. The browser is an endpoint, not a full Fabric node, and disappears when the Signal browser session closes. Disabled node outputs include a concrete reason such as `mpv missing`.


## 1.6.3 — stable Safari output picker

- Browser output selection claims the media card before asynchronous Safari playback, avoiding selector snap-back during polling.
- Audio proxying is incremental/range-preserving rather than whole-track buffered.
- Failed browser playback restores the prior node selection cleanly.

## 1.5.0 — Fabric media outputs

Signal now separates the browser controller from the playback machine. The **OUT** chooser lists reachable Fabric media outputs; direct `play ...` requests and media controls route to the selected node. Switching output during active playback hands the canonical queue/current index to the new node before stopping the old one.

Camera capture now places `what am I looking at?` into the composer as selected text. Return sends it as-is; typing replaces it.

## 1.4.0 — camera / vision attachment

Tap **CAM** beside the Signal chat input on an iPhone or other browser. The browser opens its native image capture/picker; the selected photo appears as an attachment chip. Ask a normal question such as `what am I looking at?` and submit. Tapping the attachment chip removes it before sending.

Camera capture is intentionally generic attachment plumbing rather than a hard-coded vision command. Signal accepts the image at the browser edge, writes it into the request workspace, and passes that local path to LO. LO's existing multimodal path chooses a vision-capable worker and Fabric stages the image as an artifact instead of embedding the raw bytes in a Fabric work packet.

The file-input capture path is used rather than a permanent live camera stream, so it works well on iPhone and does not require Signal to own camera state after the photo is taken.

Signal's media controller also runs correctly from sparse service environments: LOOK resolves mpv from configured PATH plus normal Linuxbrew/Homebrew/system locations.

## 1.3.0 — shared media card

Signal now discovers an active LOOK MediaSession and renders it as a compact browser card. The card is only a control/view surface: LOOK owns queue/session meaning and mpv owns decoding/playback. Starting music in a terminal therefore appears in Signal automatically, and browser controls mutate the same session. Dismiss hides the card without stopping playback; `/player` restores it.

Controls include previous, play/pause, next, stop, an expandable queue, and exact queue-item selection. The backend uses `lk media state` and deterministic media transport commands; it does not create a second browser audio player.

Small browser body for LO/LOOK with a persistent 256×256 graphics surface.

## 0.5.2

- Artwork stays visible much longer: `display` defaults to 75s hold + 25s fade; `moment` to 15s + 12s, with minimum dwell times so model hints cannot make art disappear instantly.
- Every intentional Signal drawing is automatically archived as a composed PNG plus scene JSON under `~/.local/share/signal-window/gallery/YYYY-MM-DD/`.
- `/gallery` reports the gallery location. `--gallery-dir` changes it; `--no-gallery` disables archiving.
- Includes a user-systemd service and installer so Signal can be a normal persistent 3090 service.

## Install on the 3090

```bash
./install.sh
systemctl --user status signal-window.service --no-pager
```

Then expose it privately if desired:

```bash
tailscale serve --bg --https=7331 http://127.0.0.1:7331
```

Manual development remains:

```bash
python3 server.py
```

## Fabric-attached display

Signal 1.1 follows synchronized Fabric light shows from its host node, so iPhone/iPad/browser clients can participate without becoming compute nodes. Ordinary exchanges asynchronously compose a Signal scene after the answer; image generation remains a separate explicit artifact path.
