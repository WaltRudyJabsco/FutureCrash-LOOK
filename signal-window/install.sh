#!/usr/bin/env bash
set -euo pipefail
SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="$HOME/.local/share/signal-window"
mkdir -p "$INSTALL_DIR"
install -m 0644 "$SOURCE_DIR/index.html" "$SOURCE_DIR/style.css" "$SOURCE_DIR/app.js" "$INSTALL_DIR/"
install -m 0755 "$SOURCE_DIR/server.py" "$INSTALL_DIR/server.py"
OS="$(uname -s)"
if [[ "$OS" == "Linux" ]] && command -v systemctl >/dev/null 2>&1; then
  UNIT_DIR="$HOME/.config/systemd/user"; mkdir -p "$UNIT_DIR"
  install -m 0644 "$SOURCE_DIR/signal-window.service" "$UNIT_DIR/signal-window.service"
  systemctl --user daemon-reload
  systemctl --user enable signal-window.service >/dev/null 2>&1 || true
  systemctl --user restart signal-window.service || systemctl --user start signal-window.service || true
elif [[ "$OS" == "Darwin" ]] && command -v launchctl >/dev/null 2>&1; then
  AGENT_DIR="$HOME/Library/LaunchAgents"; mkdir -p "$AGENT_DIR"
  PLIST="$AGENT_DIR/com.futurecrash.signal-window.plist"
  cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>Label</key><string>com.futurecrash.signal-window</string>
<key>ProgramArguments</key><array><string>/usr/bin/python3</string><string>$INSTALL_DIR/server.py</string></array>
<key>RunAtLoad</key><true/><key>KeepAlive</key><true/>
<key>EnvironmentVariables</key><dict><key>PATH</key><string>$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string></dict>
<key>StandardOutPath</key><string>$INSTALL_DIR/signal-window.log</string>
<key>StandardErrorPath</key><string>$INSTALL_DIR/signal-window.log</string>
</dict></plist>
EOF
  launchctl bootout "gui/$(id -u)/com.futurecrash.signal-window" >/dev/null 2>&1 || true
  launchctl bootstrap "gui/$(id -u)" "$PLIST" || true
else
  echo "Signal installed; start with: python3 $INSTALL_DIR/server.py"
fi
printf 'Signal Window 1.4.0 installed\n  app: %s\n  gallery: %s\n' "$INSTALL_DIR" "$HOME/.local/share/signal-window/gallery"
printf '  local: http://127.0.0.1:7331\n'
