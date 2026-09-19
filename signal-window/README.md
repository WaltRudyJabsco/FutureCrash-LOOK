# Signal Window 1.1.1

Signal is now a native browser body for LO. The server imports LOOK's reusable LO engine directly rather than spawning and scraping the terminal CLI. Browser sessions keep a bounded ephemeral conversation history, `/clear` clears that server-side state, and generated/browser-displayable artifacts remain presentation targets rather than worker-side desktop windows.

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
