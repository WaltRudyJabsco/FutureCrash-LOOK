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
<key>EnvironmentVariables</key><dict><key>PATH</key><string>$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string></dict>
<key>StandardOutPath</key><string>$DST/albert.log</string><key>StandardErrorPath</key><string>$DST/albert.log</string>
</dict></plist>
EOF
  launchctl bootout "gui/$(id -u)/com.futurecrash.albert" >/dev/null 2>&1 || true
  launchctl bootstrap "gui/$(id -u)" "$PLIST" || true
fi
ALBERT_HEALTH=0
for _ in $(seq 1 20); do
  if python3 - <<'PY_ALBERT_HEALTH' >/dev/null 2>&1
import urllib.request
with urllib.request.urlopen('http://127.0.0.1:7330/health', timeout=.5) as r:
    raise SystemExit(0 if r.status == 200 else 1)
PY_ALBERT_HEALTH
  then ALBERT_HEALTH=1; break; fi
  sleep .2
done
if [[ $ALBERT_HEALTH != 1 ]]; then
  echo 'Albert install failed: http://127.0.0.1:7330/health did not become ready' >&2
  if [[ "$OS" == Linux ]] && command -v systemctl >/dev/null 2>&1; then
    systemctl --user --no-pager --full status albert.service >&2 || true
  elif [[ "$OS" == Darwin ]] && [[ -f "$DST/albert.log" ]]; then
    tail -40 "$DST/albert.log" >&2 || true
  fi
  exit 1
fi
printf 'Albert 5 installed\n  local: http://127.0.0.1:7330 · ready\n'
if command -v tailscale >/dev/null 2>&1; then
  ALBERT_DNS="$(tailscale status --json 2>/dev/null | python3 -c 'import json,sys; d=json.load(sys.stdin); print(((d.get("Self") or {}).get("DNSName") or "").rstrip("."))' 2>/dev/null || true)"
  if [[ -n "$ALBERT_DNS" ]]; then
    printf '  iPad/tailnet: https://%s:7330\n' "$ALBERT_DNS"
  fi
fi
