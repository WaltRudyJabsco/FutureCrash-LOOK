#!/usr/bin/env bash
set -euo pipefail
SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="$HOME/.local/share/signal-window"
UNIT_DIR="$HOME/.config/systemd/user"
mkdir -p "$INSTALL_DIR" "$UNIT_DIR"
install -m 0644 "$SOURCE_DIR/index.html" "$SOURCE_DIR/style.css" "$SOURCE_DIR/app.js" "$INSTALL_DIR/"
install -m 0755 "$SOURCE_DIR/server.py" "$INSTALL_DIR/server.py"
install -m 0644 "$SOURCE_DIR/signal-window.service" "$UNIT_DIR/signal-window.service"
systemctl --user daemon-reload
systemctl --user enable --now signal-window.service
printf 'Signal Window 0.5.2 installed\n  app: %s\n  gallery: %s\n' "$INSTALL_DIR" "$HOME/.local/share/signal-window/gallery"
printf '  local: http://127.0.0.1:7331\n  status: systemctl --user status signal-window.service --no-pager\n'
