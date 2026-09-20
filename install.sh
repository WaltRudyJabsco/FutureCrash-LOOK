#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "Future Crash + LOOK 5.1.6 · Conversation Channels"
echo "────────────────────────────────────────"

# Refuse a mixed bundle before mutating the machine. A unified release must move
# LOOK and the node together.
EXPECTED_RELEASE="$(tr -d '[:space:]' < "$ROOT/VERSION")"
[[ "$EXPECTED_RELEASE" == "5.1.6" ]] || { echo "BUNDLE ERROR: expected release 5.1.6, found $EXPECTED_RELEASE"; exit 4; }
grep -q 'def _fabric_command' "$ROOT/look/lk" || { echo "BUNDLE ERROR: LOOK source has no Fabric command"; exit 4; }
grep -q 'choices=.*serve.*fabric' "$ROOT/core/node.py" || { echo "BUNDLE ERROR: node source has no Fabric CLI"; exit 4; }

DRY_RUN=0
UNINSTALL=0
for a in "$@"; do
  [[ "$a" == "--dry-run" ]] && DRY_RUN=1
  [[ "$a" == "--uninstall" ]] && UNINSTALL=1
done

"$ROOT/install-look.sh" "$@"
((UNINSTALL)) && exit 0
if ((DRY_RUN)); then
  echo
  echo "[dry-run] would install/restart Unified Node 5.1.6, Fabric dashboard, and Signal Window 1.1.2"
  echo "[dry-run] would reconcile Tailscale :7332 → separate fcl-ingress :7333 and verify Fabric CLI wiring"
  exit 0
fi

mkdir -p "$HOME/.local/share/future-crash-look/core" "$HOME/.local/bin"
install -m 0755 "$ROOT/core/node.py" "$HOME/.local/share/future-crash-look/core/node.py"
install -m 0644 "$ROOT/core/fabric_packet.py" "$HOME/.local/share/future-crash-look/core/fabric_packet.py"
install -m 0644 "$ROOT/core/fabric_client.py" "$HOME/.local/share/future-crash-look/core/fabric_client.py"
install -m 0644 "$ROOT/core/conductor.py" "$HOME/.local/share/future-crash-look/core/conductor.py"
install -m 0755 "$ROOT/core/fcl-node" "$HOME/.local/bin/fcl-node"
install -m 0755 "$ROOT/core/ingress.py" "$HOME/.local/share/future-crash-look/core/ingress.py"
install -m 0755 "$ROOT/core/fcl-ingress" "$HOME/.local/bin/fcl-ingress"
install -m 0644 "$ROOT/VERSION" "$HOME/.local/share/future-crash-look/RELEASE"

# Signal is an interface over the same node. Its installer owns platform service edges.
if [[ -x "$ROOT/signal-window/install.sh" ]]; then
  "$ROOT/signal-window/install.sh" || true
fi

OS="$(uname -s)"
if [[ "$OS" == "Linux" ]] && command -v systemctl >/dev/null 2>&1; then
  mkdir -p "$HOME/.config/systemd/user"
  install -m 0644 "$ROOT/core/future-crash-look-node.service" "$HOME/.config/systemd/user/future-crash-look-node.service"
  install -m 0644 "$ROOT/core/future-crash-look-ingress.service" "$HOME/.config/systemd/user/future-crash-look-ingress.service"
  systemctl --user daemon-reload
  systemctl --user enable future-crash-look-node.service future-crash-look-ingress.service >/dev/null 2>&1 || true
  systemctl --user restart future-crash-look-node.service || systemctl --user start future-crash-look-node.service || true
  systemctl --user restart future-crash-look-ingress.service || systemctl --user start future-crash-look-ingress.service || true
elif [[ "$OS" == "Darwin" ]] && command -v launchctl >/dev/null 2>&1; then
  mkdir -p "$HOME/Library/LaunchAgents"
  sed "s|__HOME__|$HOME|g" "$ROOT/core/com.futurecrash.look.node.plist" > "$HOME/Library/LaunchAgents/com.futurecrash.look.node.plist"
  sed "s|__HOME__|$HOME|g" "$ROOT/core/com.futurecrash.look.ingress.plist" > "$HOME/Library/LaunchAgents/com.futurecrash.look.ingress.plist"
  launchctl bootout "gui/$(id -u)/com.futurecrash.look.ingress" >/dev/null 2>&1 || true
  launchctl bootout "gui/$(id -u)/com.futurecrash.look.node" >/dev/null 2>&1 || true
  launchctl bootstrap "gui/$(id -u)" "$HOME/Library/LaunchAgents/com.futurecrash.look.node.plist" || true
  launchctl bootstrap "gui/$(id -u)" "$HOME/Library/LaunchAgents/com.futurecrash.look.ingress.plist" || true
else
  echo "Node installed; start with: fcl-node serve"
fi

# Keep Tailscale ingress in a different PROCESS, not merely a second socket in the
# node process. fcl-ingress bounds remote concurrency before relaying to localhost.
# Public Fabric remains https://<node>:7332; Tailscale targets localhost:7333.
if command -v tailscale >/dev/null 2>&1; then
  TAILSCALE_BACKEND="http://127.0.0.1:7333"
  if tailscale serve --bg --https=7332 "$TAILSCALE_BACKEND" >/dev/null 2>&1; then
    echo "  Tailscale node API: :7332 → guarded ingress process :7333"
  elif command -v sudo >/dev/null 2>&1 && sudo -n true >/dev/null 2>&1 && sudo -n tailscale serve --bg --https=7332 "$TAILSCALE_BACKEND" >/dev/null 2>&1; then
    echo "  Tailscale node API: :7332 → guarded ingress process :7333"
  else
    echo "  Tailscale node API: backend could not be reconciled automatically"
    echo "    run once: sudo tailscale serve --bg --https=7332 http://127.0.0.1:7333"
  fi
fi

# Give the platform service manager a moment to publish the fresh daemon before
# verifying the LOOK→Fabric path. This is a bounded startup wait, not a fixed sleep.
NODE_READY=0
for _ in {1..25}; do
  if "$HOME/.local/bin/fcl-node" pulse >/dev/null 2>&1; then NODE_READY=1; break; fi
  sleep 0.2
done
if (( ! NODE_READY )); then
  echo "INSTALL ERROR: Unified Node did not become ready on local :7332" >&2
  exit 5
fi
if ! python3 - <<'PY_CHECK' >/dev/null 2>&1
import json, urllib.request
with urllib.request.urlopen("http://127.0.0.1:7333/_fcl/metrics", timeout=1.0) as response:
    data = json.loads(response.read() or b"{}")
    assert data.get("ok") is True
PY_CHECK
then
  echo "INSTALL ERROR: Fabric ingress guard did not become ready on localhost :7333" >&2
  exit 5
fi

# Verify exact installed bytes. This catches stale LOOK/new-node split installs.
if ! cmp -s "$ROOT/look/lo_engine.py" "$HOME/.local/share/look/lo_engine.py"; then
  echo "INSTALL ERROR: installed native LO engine does not match this checkout" >&2
  exit 5
fi
if ! cmp -s "$ROOT/look/lk" "$HOME/.local/share/look/lk"; then
  echo "INSTALL ERROR: installed LOOK does not match this checkout" >&2
  exit 5
fi
if ! cmp -s "$ROOT/core/node.py" "$HOME/.local/share/future-crash-look/core/node.py"; then
  echo "INSTALL ERROR: installed node does not match this checkout" >&2
  exit 5
fi
if ! cmp -s "$ROOT/core/ingress.py" "$HOME/.local/share/future-crash-look/core/ingress.py"; then
  echo "INSTALL ERROR: installed ingress guard does not match this checkout" >&2
  exit 5
fi
if ! cmp -s "$ROOT/core/fabric_client.py" "$HOME/.local/share/future-crash-look/core/fabric_client.py"; then
  echo "INSTALL ERROR: Fabric client differs from release" >&2; exit 8
fi
if ! cmp -s "$ROOT/core/conductor.py" "$HOME/.local/share/future-crash-look/core/conductor.py"; then
  echo "INSTALL ERROR: installed conductor differs from release" >&2; exit 8
fi
if ! PYTHONPATH="$HOME/.local/share/future-crash-look/core" python3 - <<'PY_RUNTIME' >/dev/null 2>&1
import conductor, fabric_client
assert conductor.classify("ping").tier == "reflex"
assert callable(fabric_client.stream_infer)
PY_RUNTIME
then
  echo "INSTALL ERROR: installed Fabric runtime modules do not import together" >&2
  exit 8
fi
if ! cmp -s "$ROOT/core/fabric_packet.py" "$HOME/.local/share/future-crash-look/core/fabric_packet.py"; then
  echo "INSTALL ERROR: installed Fabric packet core does not match this checkout" >&2
  exit 5
fi
if ! "$HOME/.local/bin/lk" fabric pulse >/dev/null 2>&1; then
  echo "INSTALL ERROR: LOOK Fabric command did not reach the resident node" >&2
  echo "  inspect: $HOME/.local/bin/fcl-node activity" >&2
  exit 5
fi

echo
echo "Unified node installed and verified · release $EXPECTED_RELEASE"
echo "  fcl-node fabric     # human view of the compute fabric"
echo "  fcl-node models     # model capability advertisements"
echo "  fcl-node pulse      # shared heartbeat"
echo "  fcl-node activity   # supervisor truth"
echo "  fcl-node http       # local + guarded-ingress HTTP pressure"
echo "  fcl-node nodes      # peers + node advertisements"
echo "  fcl-node jobs       # durable Fabric work ledger"
