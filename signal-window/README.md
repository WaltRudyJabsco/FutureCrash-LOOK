# Signal Window 0.5.2

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
