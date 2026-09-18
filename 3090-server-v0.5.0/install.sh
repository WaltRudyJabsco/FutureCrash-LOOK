#!/usr/bin/env bash
set -euo pipefail

SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="$HOME/.local/share/3090-server"
BIN_DIR="$HOME/.local/bin"
UNIT_DIR="$HOME/.config/systemd/user"

mkdir -p "$INSTALL_DIR" "$BIN_DIR" "$UNIT_DIR"
install -m 0755 "$SOURCE_DIR/server.py" "$INSTALL_DIR/server.py"
install -m 0755 "$SOURCE_DIR/console.py" "$INSTALL_DIR/console.py"
ln -sfn "$INSTALL_DIR/server.py" "$BIN_DIR/server"

# Definitions are installed, but existing application processes are not killed or migrated.
install -m 0644 "$SOURCE_DIR/server-comfy.service" "$UNIT_DIR/server-comfy.service"
install -m 0644 "$SOURCE_DIR/server-mercury.service" "$UNIT_DIR/server-mercury.service"
install -m 0644 "$SOURCE_DIR/server-console.service" "$UNIT_DIR/server-console.service"
systemctl --user daemon-reload

# Keep the operator console available. Existing Comfy/Mercury lifecycle remains explicit.
systemctl --user enable --now server-console.service >/dev/null 2>&1 || true
systemctl --user enable server-mercury.service >/dev/null 2>&1 || true
systemctl --user enable server-comfy.service >/dev/null 2>&1 || true

cat <<TXT
3090 Home Server Controller v0.5.0 installed.
  program: $INSTALL_DIR/server.py
  console: http://127.0.0.1:3090/

No running application service was stopped or restarted.
No shell startup files were modified.

Try:
  server status
  server doctor
  server status signal
  server expose signal
TXT
