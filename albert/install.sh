#!/usr/bin/env bash
set -euo pipefail
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DST="$HOME/.local/share/albert"
mkdir -p "$DST"
install -m 0644 "$SRC/index.html" "$SRC/VERSION" "$DST/"
install -m 0755 "$SRC/server.py" "$DST/server.py"
OS="$(uname -s)"
if [[ "$OS" == Linux ]] && command -v systemctl >/dev/null 2>&1; then
  mkdir -p "$HOME/.config/systemd/user"
  install -m 0644 "$SRC/albert.service" "$HOME/.config/systemd/user/albert.service"
  systemctl --user daemon-reload
  systemctl --user enable albert.service >/dev/null 2>&1 || true
  systemctl --user restart albert.service || systemctl --user start albert.service || true
elif [[ "$OS" == Darwin ]] && command -v launchctl >/dev/null 2>&1; then
  mkdir -p "$HOME/Library/LaunchAgents"
  PLIST="$HOME/Library/LaunchAgents/com.futurecrash.albert.plist"
  cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>Label</key><string>com.futurecrash.albert</string>
<key>ProgramArguments</key><array><string>/usr/bin/python3</string><string>$DST/server.py</string></array>
<key>RunAtLoad</key><true/><key>KeepAlive</key><true/>
<key>StandardOutPath</key><string>$DST/albert.log</string><key>StandardErrorPath</key><string>$DST/albert.log</string>
</dict></plist>
EOF
  launchctl bootout "gui/$(id -u)/com.futurecrash.albert" >/dev/null 2>&1 || true
  launchctl bootstrap "gui/$(id -u)" "$PLIST" || true
fi
printf 'Albert 5 installed\n  local: http://127.0.0.1:7330\n'
