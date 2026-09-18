LOCAL LABS BASELINE · 2026-09-17

Pinned working set:
  Future Crash + LOOK  3.3.10
  Signal Window        0.5.2
  3090 Server          0.5.0

Recommended 3090 order:

1. LOOK
   unzip future-crash-look-3.3.10.zip
   cd future-crash-look-3.3.10
   ./install.sh
   exec zsh

2. Signal Window
   unzip signal-window-v0.5.2.zip
   cd signal-window-v0.5.2/signal-window
   ./install.sh

3. 3090 Server
   unzip 3090-server-v0.5.0.zip
   cd 3090-server-v0.5.0
   ./install.sh

4. Verify
   server version
   server status
   server doctor
   server status signal

5. Tailnet exposure (explicit, never automatic)
   server expose signal

Signal gallery:
  ~/.local/share/signal-window/gallery/YYYY-MM-DD/

This bundle does not include Mercury Writer or ComfyUI application payloads.
The 3090 controller discovers/manages their existing installations.
