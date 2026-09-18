#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "Future Crash + LOOK 4.0 · Unified Node"
echo "────────────────────────────────────────"
"$ROOT/install-look.sh" "$@"
# Uninstall is owned by the legacy installer for now; don't reinstall components afterward.
for a in "$@"; do [[ "$a" == "--uninstall" ]] && exit 0; done
mkdir -p "$HOME/.local/share/future-crash-look/core" "$HOME/.local/bin"
cp "$ROOT/core/node.py" "$HOME/.local/share/future-crash-look/core/node.py"
cp "$ROOT/core/fcl-node" "$HOME/.local/bin/fcl-node"; chmod +x "$HOME/.local/bin/fcl-node"
# Signal is an interface, not a separate product installation anymore.
if [[ -x "$ROOT/signal-window/install.sh" ]]; then "$ROOT/signal-window/install.sh" --no-start 2>/dev/null || "$ROOT/signal-window/install.sh" 2>/dev/null || true; fi
OS="$(uname -s)"
if [[ "$OS" == "Linux" ]] && command -v systemctl >/dev/null 2>&1; then
  mkdir -p "$HOME/.config/systemd/user"; cp "$ROOT/core/future-crash-look-node.service" "$HOME/.config/systemd/user/"
  systemctl --user daemon-reload; systemctl --user enable --now future-crash-look-node.service || true
elif [[ "$OS" == "Darwin" ]] && command -v launchctl >/dev/null 2>&1; then
  mkdir -p "$HOME/Library/LaunchAgents"; sed "s|__HOME__|$HOME|g" "$ROOT/core/com.futurecrash.look.node.plist" > "$HOME/Library/LaunchAgents/com.futurecrash.look.node.plist"
  launchctl bootout "gui/$(id -u)/com.futurecrash.look.node" >/dev/null 2>&1 || true
  launchctl bootstrap "gui/$(id -u)" "$HOME/Library/LaunchAgents/com.futurecrash.look.node.plist" || true
else
  echo "Node installed; start with: fcl-node serve"
fi
echo
echo "Unified node installed."
echo "  fcl-node status"
echo "  fcl-node activity"
echo "  fcl-node nodes"
