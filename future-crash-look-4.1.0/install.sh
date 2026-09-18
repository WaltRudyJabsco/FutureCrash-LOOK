#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "Future Crash + LOOK 4.1 · Fabric Pulse"
echo "────────────────────────────────────────"
"$ROOT/install-look.sh" "$@"
for a in "$@"; do [[ "$a" == "--uninstall" ]] && exit 0; done
mkdir -p "$HOME/.local/share/future-crash-look/core" "$HOME/.local/bin"
install -m 0755 "$ROOT/core/node.py" "$HOME/.local/share/future-crash-look/core/node.py"
install -m 0755 "$ROOT/core/fcl-node" "$HOME/.local/bin/fcl-node"

# Signal is an interface over the same node. Its installer owns platform service edges.
if [[ -x "$ROOT/signal-window/install.sh" ]]; then
  "$ROOT/signal-window/install.sh" || true
fi

OS="$(uname -s)"
if [[ "$OS" == "Linux" ]] && command -v systemctl >/dev/null 2>&1; then
  mkdir -p "$HOME/.config/systemd/user"
  install -m 0644 "$ROOT/core/future-crash-look-node.service" "$HOME/.config/systemd/user/future-crash-look-node.service"
  systemctl --user daemon-reload
  systemctl --user enable future-crash-look-node.service >/dev/null 2>&1 || true
  systemctl --user restart future-crash-look-node.service || systemctl --user start future-crash-look-node.service || true
elif [[ "$OS" == "Darwin" ]] && command -v launchctl >/dev/null 2>&1; then
  mkdir -p "$HOME/Library/LaunchAgents"
  sed "s|__HOME__|$HOME|g" "$ROOT/core/com.futurecrash.look.node.plist" > "$HOME/Library/LaunchAgents/com.futurecrash.look.node.plist"
  launchctl bootout "gui/$(id -u)/com.futurecrash.look.node" >/dev/null 2>&1 || true
  launchctl bootstrap "gui/$(id -u)" "$HOME/Library/LaunchAgents/com.futurecrash.look.node.plist" || true
else
  echo "Node installed; start with: fcl-node serve"
fi

# The node is the one shared network endpoint. Publish it when Tailscale is present.
# Never block installation for privilege escalation; report the exact repair if needed.
if command -v tailscale >/dev/null 2>&1; then
  if ! tailscale serve status 2>/dev/null | grep -q ':7332'; then
    if tailscale serve --bg --https=7332 http://127.0.0.1:7332 >/dev/null 2>&1; then
      echo "  Tailscale node API: published on :7332"
    elif command -v sudo >/dev/null 2>&1 && sudo -n true >/dev/null 2>&1 && sudo -n tailscale serve --bg --https=7332 http://127.0.0.1:7332 >/dev/null 2>&1; then
      echo "  Tailscale node API: published on :7332"
    else
      echo "  Tailscale node API: not yet published"
      echo "    run once: sudo tailscale serve --bg --https=7332 http://127.0.0.1:7332"
    fi
  else
    echo "  Tailscale node API: :7332 already published"
  fi
fi

echo
echo "Unified node installed."
echo "  fcl-node fabric     # human view of the compute fabric"
echo "  fcl-node models     # model capability advertisements"
echo "  fcl-node pulse      # shared heartbeat"
echo "  fcl-node activity   # supervisor truth"
echo "  fcl-node nodes      # peers + node advertisements"
