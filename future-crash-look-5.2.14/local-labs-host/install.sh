#!/usr/bin/env bash
set -euo pipefail

SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="$HOME/.local/share/local-labs-host"
LEGACY_DIR="$HOME/.local/share/3090-server"
BIN_DIR="$HOME/.local/bin"
OS="$(uname -s)"

mkdir -p "$INSTALL_DIR" "$BIN_DIR"
install -m 0755 "$SOURCE_DIR/server.py" "$INSTALL_DIR/server.py"
install -m 0755 "$SOURCE_DIR/console.py" "$INSTALL_DIR/console.py"
ln -sfn "$INSTALL_DIR/server.py" "$BIN_DIR/server"

if [[ "$OS" == "Linux" ]] && command -v systemctl >/dev/null 2>&1; then
  UNIT_DIR="$HOME/.config/systemd/user"
  mkdir -p "$UNIT_DIR"
  # Linux service definitions remain native systemd units. The controller's
  # public contract is OS-neutral; another host may use another service manager.
  install -m 0644 "$SOURCE_DIR/server-comfy.service" "$UNIT_DIR/server-comfy.service"
  install -m 0644 "$SOURCE_DIR/server-mercury.service" "$UNIT_DIR/server-mercury.service"
  install -m 0644 "$SOURCE_DIR/server-console.service" "$UNIT_DIR/server-console.service"
  systemctl --user daemon-reload
  systemctl --user enable --now server-console.service >/dev/null 2>&1 || true
  systemctl --user enable server-mercury.service >/dev/null 2>&1 || true
  systemctl --user enable server-comfy.service >/dev/null 2>&1 || true
elif [[ "$OS" == "Darwin" ]]; then
  # Discovery/status is usable on macOS today. Application lifecycle stays
  # explicit until each service has a reviewed launchd definition; do not fake
  # Linux/systemd semantics on a Mac.
  :
fi

cat <<TXT
Local Labs Host Controller v0.5.1 installed.
  program: $INSTALL_DIR/server.py
  platform: $OS

No running application service was stopped or restarted.
No shell startup files were modified.

Try:
  server status
  server doctor
  server status signal
TXT
