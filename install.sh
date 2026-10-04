#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "Future Crash + LOOK 8.8.1 · EXECUTION HOTFIX"
echo "────────────────────────────────────────"

# Refuse a mixed bundle before mutating the machine. A unified release must move
# LOOK and the node together.
EXPECTED_RELEASE="$(tr -d '[:space:]' < "$ROOT/VERSION")"
[[ "$EXPECTED_RELEASE" == "8.8.1" ]] || { echo "BUNDLE ERROR: expected release 8.8.1, found $EXPECTED_RELEASE"; exit 4; }
echo "BUNDLE SOURCE  $ROOT"
echo "BUNDLE RELEASE $EXPECTED_RELEASE · FABRIC VISION"
LOOK_COMPONENT_VERSION="$(tr -d '[:space:]' < "$ROOT/look/VERSION")"
FUTURE_CRASH_COMPONENT_VERSION="$(tr -d '[:space:]' < "$ROOT/future-crash/VERSION")"
ALBERT_COMPONENT_VERSION="$(tr -d '[:space:]' < "$ROOT/albert/VERSION")"
[[ "$LOOK_COMPONENT_VERSION" == "4.56.1" ]] || { echo "BUNDLE ERROR: LOOK component reports $LOOK_COMPONENT_VERSION, expected 4.56.1"; exit 4; }
[[ "$FUTURE_CRASH_COMPONENT_VERSION" == "1.2.2" ]] || { echo "BUNDLE ERROR: Future Crash component reports $FUTURE_CRASH_COMPONENT_VERSION, expected 1.2.2"; exit 4; }
[[ "$ALBERT_COMPONENT_VERSION" == "$EXPECTED_RELEASE" ]] || { echo "BUNDLE ERROR: Albert integration reports $ALBERT_COMPONENT_VERSION, expected $EXPECTED_RELEASE"; exit 4; }
python3 - "$ROOT" "$EXPECTED_RELEASE" <<'PY_BUNDLE'
import re,sys
from pathlib import Path
root=Path(sys.argv[1]); expected=sys.argv[2]
checks=[
    (root/'core/node.py', r'^VERSION = "([^"]+)"', 'node'),
    (root/'core/ingress.py', r'^VERSION = "([^"]+)"', 'ingress'),
    (root/'core/tailcat.py', r'^VERSION = "([^"]+)"', 'tailcat'),
    (root/'core/rendezvous.py', r'^VERSION = "([^"]+)"', 'rendezvous'),
]
for path,pat,label in checks:
    m=re.search(pat,path.read_text(),re.M)
    got=m.group(1) if m else '<missing>'
    if got != expected:
        raise SystemExit(f'BUNDLE ERROR: {label} reports {got}, expected {expected}')
PY_BUNDLE
grep -q 'def _fabric_command' "$ROOT/look/lk" || { echo "BUNDLE ERROR: LOOK source has no Fabric command"; exit 4; }
LOOK_SOURCE_VERSION="$(sed -n 's/^VERSION="\([^"]*\)"/\1/p' "$ROOT/look/lk" | head -n1)"
LOOK_DECLARED_VERSION="$(sed -n 's/^LOOK_VERSION="\([^"]*\)"/\1/p' "$ROOT/install-look.sh" | head -n1)"
[[ -n "$LOOK_SOURCE_VERSION" && "$LOOK_SOURCE_VERSION" == "$LOOK_DECLARED_VERSION" ]] || { echo "BUNDLE ERROR: LOOK source reports ${LOOK_SOURCE_VERSION:-missing}, installer declares ${LOOK_DECLARED_VERSION:-missing}"; exit 4; }
grep -q 'choices=.*serve.*fabric' "$ROOT/core/node.py" || { echo "BUNDLE ERROR: node source has no Fabric CLI"; exit 4; }

DRY_RUN=0
UNINSTALL=0
OPENJEV_MODE="${FCL_OPENJEV_MODE:-auto}"
for a in "$@"; do
  [[ "$a" == "--dry-run" ]] && DRY_RUN=1
  [[ "$a" == "--uninstall" ]] && UNINSTALL=1
  [[ "$a" == "--openjev=off" ]] && OPENJEV_MODE="off"
  [[ "$a" == "--openjev=auto" ]] && OPENJEV_MODE="auto"
  [[ "$a" == "--openjev=adopt" ]] && OPENJEV_MODE="adopt"
  [[ "$a" == "--openjev=install" ]] && OPENJEV_MODE="install"
done
case "$OPENJEV_MODE" in off|auto|adopt|install) ;; *) echo "BUNDLE ERROR: invalid --openjev mode: $OPENJEV_MODE"; exit 4;; esac

FCL_UNIFIED_INSTALL_CHILD=1 "$ROOT/install-look.sh" "$@"
((UNINSTALL)) && exit 0
if ((DRY_RUN)); then
  echo
  echo "[dry-run] would install/restart Unified Node 8.8.1 · EXECUTION HOTFIX with signed Fabric rendezvous, Tailcat direct transport, ONE BRAIN cognition, LIVING MIND memory, browser endpoints, SearXNG, Media, Artifacts, and Signal Window 1.11.0"
  echo "[dry-run] OpenJev mode: $OPENJEV_MODE (auto provisions on capable nodes; absence/failure is non-fatal)"
  echo "[dry-run] would initialize Tailcat :7443, install optional signed rendezvous discovery, keep Tailscale :7332 → fcl-ingress :7333 as fallback, and verify Fabric CLI wiring"
  exit 0
fi

# The installer owns the managed node lifecycle while it runs. Once we stop or
# unload that job, every exit path must put it back. Do not infer ownership from
# port 7332: other transports may legitimately expose the same port on other
# interfaces, and systemd/launchd are the source of truth for this service.
MANAGED_NODE_RETIRED=0
INSTALL_COMPLETE=0
restore_node_on_failure() {
  local status=$?
  if (( status != 0 && INSTALL_COMPLETE == 0 && MANAGED_NODE_RETIRED == 1 )); then
    echo "  install failed · restoring Unified Node" >&2
    if [[ "$(uname -s)" == "Linux" ]] && command -v systemctl >/dev/null 2>&1; then
      systemctl --user start future-crash-look-node.service >/dev/null 2>&1 || true
    elif [[ "$(uname -s)" == "Darwin" ]] && command -v launchctl >/dev/null 2>&1; then
      launchctl bootstrap "gui/$(id -u)" "$HOME/Library/LaunchAgents/com.futurecrash.look.node.plist" >/dev/null 2>&1 || true
      launchctl kickstart -k "gui/$(id -u)/com.futurecrash.look.node" >/dev/null 2>&1 || true
    fi
  fi
  return "$status"
}
trap restore_node_on_failure EXIT

retire_resident_node() {
  local os
  os="$(uname -s)"
  if [[ "$os" == "Linux" ]] && command -v systemctl >/dev/null 2>&1; then
    systemctl --user stop future-crash-look-node.service >/dev/null 2>&1 || true
    MANAGED_NODE_RETIRED=1
  elif [[ "$os" == "Darwin" ]] && command -v launchctl >/dev/null 2>&1; then
    launchctl bootout "gui/$(id -u)/com.futurecrash.look.node" >/dev/null 2>&1 || true
  launchctl bootout "gui/$(id -u)/com.futurecrash.look.media-watch" >/dev/null 2>&1 || true
    MANAGED_NODE_RETIRED=1
  fi
}

retire_resident_node

# launchd can occasionally leave the previous Python child alive after bootout.
# Retire only a listener we can prove belongs to this install; never kill an
# arbitrary process just because it owns the Fabric port.
retire_stale_macos_node_listener() {
  [[ "$(uname -s)" == "Darwin" ]] || return 0
  command -v lsof >/dev/null 2>&1 || return 0
  local deadline=$((SECONDS+5)) pid cmd
  while (( SECONDS < deadline )); do
    pid="$(lsof -nP -t -iTCP@127.0.0.1:7332 -sTCP:LISTEN 2>/dev/null | head -n1 || true)"
    [[ -z "$pid" ]] && return 0
    sleep 0.2
  done
  pid="$(lsof -nP -t -iTCP@127.0.0.1:7332 -sTCP:LISTEN 2>/dev/null | head -n1 || true)"
  [[ -z "$pid" ]] && return 0
  cmd="$(ps -p "$pid" -o command= 2>/dev/null || true)"
  case "$cmd" in
    *"$HOME/.local/bin/fcl-node"*|*"$HOME/.local/share/future-crash-look/core/node.py"*)
      echo "  retiring stale Unified Node pid $pid from :7332"
      kill -TERM "$pid" >/dev/null 2>&1 || true
      for _ in {1..25}; do
        kill -0 "$pid" >/dev/null 2>&1 || break
        sleep 0.2
      done
      if kill -0 "$pid" >/dev/null 2>&1; then
        echo "  stale Unified Node ignored TERM; forcing pid $pid"
        kill -KILL "$pid" >/dev/null 2>&1 || true
      fi
      ;;
    *)
      echo "INSTALL ERROR: localhost :7332 is owned by an unmanaged process" >&2
      echo "  pid $pid · $cmd" >&2
      exit 5
      ;;
  esac
  for _ in {1..25}; do
    if ! lsof -nP -t -iTCP@127.0.0.1:7332 -sTCP:LISTEN >/dev/null 2>&1; then return 0; fi
    sleep 0.2
  done
  echo "INSTALL ERROR: stale Unified Node did not release localhost :7332" >&2
  exit 5
}
retire_stale_macos_node_listener

mkdir -p "$HOME/.local/share/future-crash-look/core" "$HOME/.local/bin"
install -m 0755 "$ROOT/core/node.py" "$HOME/.local/share/future-crash-look/core/node.py"
install -m 0644 "$ROOT/core/fabric_packet.py" "$HOME/.local/share/future-crash-look/core/fabric_packet.py"
install -m 0644 "$ROOT/core/fabric_client.py" "$HOME/.local/share/future-crash-look/core/fabric_client.py"
install -m 0644 "$ROOT/core/fabric_vision.py" "$HOME/.local/share/future-crash-look/core/fabric_vision.py"
install -m 0644 "$ROOT/core/fabric_identity.py" "$HOME/.local/share/future-crash-look/core/fabric_identity.py"
install -m 0644 "$ROOT/core/endpoint_auth.py" "$HOME/.local/share/future-crash-look/core/endpoint_auth.py"
install -m 0644 "$ROOT/core/intent_normalizer.py" "$HOME/.local/share/future-crash-look/core/intent_normalizer.py"
install -m 0644 "$ROOT/core/jev.py" "$HOME/.local/share/future-crash-look/core/jev.py"
install -m 0644 "$ROOT/core/capability_curator.py" "$HOME/.local/share/future-crash-look/core/capability_curator.py"
install -m 0644 "$ROOT/core/conductor.py" "$HOME/.local/share/future-crash-look/core/conductor.py"
install -m 0644 "$ROOT/core/decision.py" "$HOME/.local/share/future-crash-look/core/decision.py"
install -m 0644 "$ROOT/core/cognition.py" "$HOME/.local/share/future-crash-look/core/cognition.py"
install -m 0644 "$ROOT/core/world_state.py" "$HOME/.local/share/future-crash-look/core/world_state.py"
install -m 0644 "$ROOT/core/live_state.py" "$HOME/.local/share/future-crash-look/core/live_state.py"
install -m 0644 "$ROOT/core/observation.py" "$HOME/.local/share/future-crash-look/core/observation.py"
install -m 0644 "$ROOT/core/attention.py" "$HOME/.local/share/future-crash-look/core/attention.py"
install -m 0644 "$ROOT/core/memory_store.py" "$HOME/.local/share/future-crash-look/core/memory_store.py"
install -m 0644 "$ROOT/core/ui_model.py" "$HOME/.local/share/future-crash-look/core/ui_model.py"
install -m 0755 "$ROOT/core/fcl-node" "$HOME/.local/bin/fcl-node"
install -m 0755 "$ROOT/core/ingress.py" "$HOME/.local/share/future-crash-look/core/ingress.py"
install -m 0755 "$ROOT/core/fcl-ingress" "$HOME/.local/bin/fcl-ingress"
install -m 0755 "$ROOT/core/tailcat.py" "$HOME/.local/share/future-crash-look/core/tailcat.py"
install -m 0755 "$ROOT/core/fcl-tailcat" "$HOME/.local/bin/fcl-tailcat"
install -m 0644 "$ROOT/core/rendezvous.py" "$HOME/.local/share/future-crash-look/core/rendezvous.py"
install -m 0755 "$ROOT/core/fcl-rendezvous" "$HOME/.local/bin/fcl-rendezvous"
install -m 0755 "$ROOT/core/fcl-openjev-worker" "$HOME/.local/bin/fcl-openjev-worker"
install -m 0644 "$ROOT/VERSION" "$HOME/.local/share/future-crash-look/RELEASE"
# Create the machine's Fabric keypair once. It is independent of Tailscale and
# survives normal upgrades; private key material never leaves this host.
if command -v ssh-keygen >/dev/null 2>&1 || command -v openssl >/dev/null 2>&1; then
  PYTHONPATH="$HOME/.local/share/future-crash-look/core${PYTHONPATH:+:$PYTHONPATH}" python3 -m fabric_identity init >/dev/null
  echo "  Fabric identity: ready · accountless ed25519 node identity"
else
  echo "  Fabric identity: no Ed25519 key generator found · install OpenSSH client or OpenSSL"
fi

TAILCAT_READY=0
if command -v openssl >/dev/null 2>&1; then
  if PYTHONPATH="$HOME/.local/share/future-crash-look/core${PYTHONPATH:+:$PYTHONPATH}" "$HOME/.local/bin/fcl-tailcat" init >/dev/null 2>&1; then
    TAILCAT_READY=1
    echo "  Tailcat: native TLS identity ready · direct Fabric transport on :7443"
  else
    echo "  Tailcat: TLS initialization failed · Tailscale/LAN fallback remains available"
  fi
else
  echo "  Tailcat: openssl unavailable · native TLS transport disabled; Tailscale fallback remains available"
fi

# Keep the optional Local Labs server controller in lockstep when this machine uses it.
# Upgrade both legacy and canonical locations if present, then normalize ~/.local/bin/server
# to the canonical controller. Machines without a server controller remain untouched.
SERVER_PRESENT=0
[[ -e "$HOME/.local/bin/server" ]] && SERVER_PRESENT=1
[[ -d "$HOME/.local/share/local-labs-host" ]] && SERVER_PRESENT=1
[[ -d "$HOME/.local/share/3090-server" ]] && SERVER_PRESENT=1
if [[ "$SERVER_PRESENT" == "1" ]]; then
  mkdir -p "$HOME/.local/share/local-labs-host" "$HOME/.local/bin"
  install -m 0755 "$ROOT/local-labs-host/server.py" "$HOME/.local/share/local-labs-host/server.py"
  [[ -d "$HOME/.local/share/3090-server" ]] && install -m 0755 "$ROOT/local-labs-host/server.py" "$HOME/.local/share/3090-server/server.py"
  ln -sfn "$HOME/.local/share/local-labs-host/server.py" "$HOME/.local/bin/server"
  if python3 - <<'PY_SEARX' >/dev/null 2>&1
import socket
s=socket.socket(); s.settimeout(.15)
try: s.connect(("127.0.0.1",8888)); ok=True
except OSError: ok=False
finally: s.close()
raise SystemExit(0 if ok else 1)
PY_SEARX
  then
    echo "  Web search: local SearXNG detected · Fabric web.search will advertise it"
  else
    echo "  Web search: accountless SearXNG available via: server install searxng"
  fi
fi

# Signal is an interface over the same node. Its installer owns platform service edges.
if [[ -x "$ROOT/signal-window/install.sh" ]]; then
  "$ROOT/signal-window/install.sh" || true
fi

# Albert is the quiet browser surface over the same Fabric cognition/action plane.
if [[ -x "$ROOT/albert/install.sh" ]]; then
  "$ROOT/albert/install.sh"
fi

# Capability curation is automatic and non-destructive. Discovery records the
# adapters this machine can actually expose; successful ordinary use later
# upgrades discovered adapters to proven ones.
PYTHONPATH="$HOME/.local/share/future-crash-look/core${PYTHONPATH:+:$PYTHONPATH}" python3 - <<'PY_CAPS' || true
import capability_curator
capability_curator.refresh()
PY_CAPS

# JEV-1 is the optional learned judgment tier. JEV-0 deterministic trees are
# always installed. In auto mode, capable nodes (>=12 GiB RAM) provision JEV-1;
# failure is graceful and never blocks the deterministic/local-LLM stack.
OPENJEV_ROOT="$HOME/.local/share/open-jev"
OPENJEV_CHECKPOINT="$OPENJEV_ROOT/models/Open-Jev-2B/package/checkpoint"
OPENJEV_READY=0
if [[ "$OPENJEV_MODE" == "auto" && ( ! -x "$OPENJEV_ROOT/.venv/bin/python" || ! -e "$OPENJEV_CHECKPOINT" ) ]]; then
  MEM_GIB=0
  if [[ "$(uname -s)" == "Darwin" ]]; then MEM_GIB=$(( $(sysctl -n hw.memsize 2>/dev/null || echo 0) / 1073741824 ));
  elif [[ -r /proc/meminfo ]]; then MEM_GIB=$(( $(awk '/MemTotal/{print $2}' /proc/meminfo) / 1048576 )); fi
  if (( MEM_GIB >= 12 )) && command -v git >/dev/null 2>&1 && command -v python3 >/dev/null 2>&1; then
    OPENJEV_MODE="install"
    echo "JEV-1 · capable node (${MEM_GIB} GiB) · provisioning local decision worker"
  else
    OPENJEV_MODE="adopt"
    echo "JEV-1 · auto skipped local provisioning (${MEM_GIB} GiB or prerequisites unavailable)"
  fi
fi
if [[ "$OPENJEV_MODE" == "install" && ! -x "$OPENJEV_ROOT/.venv/bin/python" ]]; then
  echo "OpenJev · installing optional decision worker"
  command -v git >/dev/null 2>&1 || { echo "OpenJev install skipped: git unavailable"; OPENJEV_MODE="off"; }
  if [[ "$OPENJEV_MODE" != "off" ]]; then
    mkdir -p "$(dirname "$OPENJEV_ROOT")"
    git clone https://github.com/Zefan-Cai/Open-Jev.git "$OPENJEV_ROOT" || { echo "OpenJev clone failed · continuing without learned decision worker"; OPENJEV_MODE="off"; }
  fi
fi
if [[ "$OPENJEV_MODE" == "install" && -d "$OPENJEV_ROOT" ]]; then
  if [[ ! -x "$OPENJEV_ROOT/.venv/bin/python" ]]; then
    python3 -m venv "$OPENJEV_ROOT/.venv" || true
    "$OPENJEV_ROOT/.venv/bin/python" -m pip install -U pip >/dev/null 2>&1 || true
    (cd "$OPENJEV_ROOT" && .venv/bin/python -m pip install -e '.[train]') || true
  fi
  if [[ ! -e "$OPENJEV_CHECKPOINT" && -x "$OPENJEV_ROOT/.venv/bin/python" ]]; then
    "$OPENJEV_ROOT/.venv/bin/python" -m pip install -q huggingface_hub || true
    if [[ -x "$OPENJEV_ROOT/.venv/bin/hf" ]]; then
      "$OPENJEV_ROOT/.venv/bin/hf" download ZefanCai/Open-Jev-2B \
        --revision 0c7aa498b1627be8da4acf34c863ff0ee0a92785 \
        --local-dir "$OPENJEV_ROOT/models/Open-Jev-2B" || true
    fi
  fi
fi
if [[ "$OPENJEV_MODE" != "off" && -x "$OPENJEV_ROOT/.venv/bin/python" && -e "$OPENJEV_CHECKPOINT" ]]; then
  OPENJEV_READY=1
elif [[ "$OPENJEV_MODE" == "adopt" ]]; then
  echo "OpenJev adopt requested but no compatible install was found · continuing without it"
fi

mkdir -p "$HOME/.config/future-crash-look"
python3 - "$HOME/.config/future-crash-look/config.json" "$OPENJEV_READY" <<'PY_CONFIG'
import json,sys
from pathlib import Path
path=Path(sys.argv[1]); ready=bool(int(sys.argv[2]))
try: data=json.loads(path.read_text())
except Exception: data={}
if not isinstance(data,dict): data={}
decision=data.get("decision") if isinstance(data.get("decision"),dict) else {}
decision.update({"enabled":ready,"provider":"openjev","url":"http://127.0.0.1:8791","mode":"live" if ready else "fallback"})
data["decision"]=decision
path.write_text(json.dumps(data,indent=2,sort_keys=True)+"\n")
path.chmod(0o600)
PY_CONFIG

OS="$(uname -s)"
if [[ "$OS" == "Linux" ]] && command -v systemctl >/dev/null 2>&1; then
  mkdir -p "$HOME/.config/systemd/user"
  install -m 0644 "$ROOT/core/future-crash-look-node.service" "$HOME/.config/systemd/user/future-crash-look-node.service"
  install -m 0644 "$ROOT/core/future-crash-look-ingress.service" "$HOME/.config/systemd/user/future-crash-look-ingress.service"
  install -m 0644 "$ROOT/core/future-crash-look-media-watch.service" "$HOME/.config/systemd/user/future-crash-look-media-watch.service"
  install -m 0644 "$ROOT/core/future-crash-look-tailcat.service" "$HOME/.config/systemd/user/future-crash-look-tailcat.service"
  install -m 0644 "$ROOT/core/future-crash-look-openjev.service" "$HOME/.config/systemd/user/future-crash-look-openjev.service"
  systemctl --user daemon-reload
  systemctl --user enable future-crash-look-node.service future-crash-look-ingress.service future-crash-look-media-watch.service >/dev/null 2>&1 || true
  if (( TAILCAT_READY )); then systemctl --user enable future-crash-look-tailcat.service >/dev/null 2>&1 || true; else systemctl --user disable --now future-crash-look-tailcat.service >/dev/null 2>&1 || true; fi
  if (( OPENJEV_READY )); then
    systemctl --user enable future-crash-look-openjev.service >/dev/null 2>&1 || true
    if python3 - <<'PY_JEV' >/dev/null 2>&1
import socket
s=socket.socket(); s.settimeout(.2)
try: s.connect(("127.0.0.1",8791)); ok=True
except OSError: ok=False
finally: s.close()
raise SystemExit(0 if ok else 1)
PY_JEV
    then
      # Do not kill an already-working manually launched experiment just to claim it.
      # The unit is enabled and will become lifecycle authority on the next clean start.
      echo "  OpenJev decision worker: existing :8791 adopted · systemd unit enabled"
    else
      systemctl --user restart future-crash-look-openjev.service || systemctl --user start future-crash-look-openjev.service || true
      echo "  OpenJev decision worker: configured on 127.0.0.1:8791"
    fi
  else
    systemctl --user disable --now future-crash-look-openjev.service >/dev/null 2>&1 || true
    echo "  OpenJev decision worker: optional/unavailable · Fabric fallback active"
  fi
  systemctl --user restart future-crash-look-node.service || systemctl --user start future-crash-look-node.service || true
  systemctl --user restart future-crash-look-ingress.service || systemctl --user start future-crash-look-ingress.service || true
  systemctl --user restart future-crash-look-media-watch.service || systemctl --user start future-crash-look-media-watch.service || true
  if (( TAILCAT_READY )); then systemctl --user restart future-crash-look-tailcat.service || systemctl --user start future-crash-look-tailcat.service || true; fi
elif [[ "$OS" == "Darwin" ]] && command -v launchctl >/dev/null 2>&1; then
  mkdir -p "$HOME/Library/LaunchAgents" "$HOME/.local/state/future-crash-look"
  sed "s|__HOME__|$HOME|g" "$ROOT/core/com.futurecrash.look.node.plist" > "$HOME/Library/LaunchAgents/com.futurecrash.look.node.plist"
  sed "s|__HOME__|$HOME|g" "$ROOT/core/com.futurecrash.look.ingress.plist" > "$HOME/Library/LaunchAgents/com.futurecrash.look.ingress.plist"
  sed "s|__HOME__|$HOME|g" "$ROOT/core/com.futurecrash.look.media-watch.plist" > "$HOME/Library/LaunchAgents/com.futurecrash.look.media-watch.plist"
  if (( TAILCAT_READY )); then sed "s|__HOME__|$HOME|g" "$ROOT/core/com.futurecrash.look.tailcat.plist" > "$HOME/Library/LaunchAgents/com.futurecrash.look.tailcat.plist"; fi
  if (( OPENJEV_READY )); then sed "s|__HOME__|$HOME|g" "$ROOT/core/com.futurecrash.look.openjev.plist" > "$HOME/Library/LaunchAgents/com.futurecrash.look.openjev.plist"; fi
  launchctl bootout "gui/$(id -u)/com.futurecrash.look.ingress" >/dev/null 2>&1 || true
  launchctl bootout "gui/$(id -u)/com.futurecrash.look.tailcat" >/dev/null 2>&1 || true
  launchctl bootout "gui/$(id -u)/com.futurecrash.look.node" >/dev/null 2>&1 || true
  launchctl bootout "gui/$(id -u)/com.futurecrash.look.media-watch" >/dev/null 2>&1 || true
  launchctl bootout "gui/$(id -u)/com.futurecrash.look.openjev" >/dev/null 2>&1 || true
  if ! launchctl bootstrap "gui/$(id -u)" "$HOME/Library/LaunchAgents/com.futurecrash.look.node.plist"; then
    echo "INSTALL ERROR: Unified Node launchctl bootstrap failed" >&2
    launchctl print "gui/$(id -u)/com.futurecrash.look.node" >&2 2>/dev/null || true
    exit 5
  fi
  if ! launchctl kickstart -k "gui/$(id -u)/com.futurecrash.look.node"; then
    echo "INSTALL ERROR: Unified Node launchctl kickstart failed" >&2
    launchctl print "gui/$(id -u)/com.futurecrash.look.node" >&2 2>/dev/null || true
    exit 5
  fi
  if (( OPENJEV_READY )); then launchctl bootstrap "gui/$(id -u)" "$HOME/Library/LaunchAgents/com.futurecrash.look.openjev.plist" || true; fi
  if ! launchctl bootstrap "gui/$(id -u)" "$HOME/Library/LaunchAgents/com.futurecrash.look.ingress.plist"; then
    echo "INSTALL ERROR: Fabric ingress launchctl bootstrap failed" >&2
    launchctl print "gui/$(id -u)/com.futurecrash.look.ingress" >&2 2>/dev/null || true
    exit 5
  fi
  if ! launchctl kickstart -k "gui/$(id -u)/com.futurecrash.look.ingress"; then
    echo "INSTALL ERROR: Fabric ingress launchctl kickstart failed" >&2
    launchctl print "gui/$(id -u)/com.futurecrash.look.ingress" >&2 2>/dev/null || true
    exit 5
  fi
  launchctl bootstrap "gui/$(id -u)" "$HOME/Library/LaunchAgents/com.futurecrash.look.media-watch.plist" || true
  launchctl kickstart -k "gui/$(id -u)/com.futurecrash.look.media-watch" >/dev/null 2>&1 || true
  if (( TAILCAT_READY )); then
    launchctl bootstrap "gui/$(id -u)" "$HOME/Library/LaunchAgents/com.futurecrash.look.tailcat.plist" || true
    # bootstrap+RunAtLoad is normally enough, but explicitly kick the encrypted
    # ingress so a freshly installed Mac cannot advertise :7443 without listening.
    launchctl kickstart -k "gui/$(id -u)/com.futurecrash.look.tailcat" >/dev/null 2>&1 || true
  fi
else
  echo "Node installed; start with: fcl-node serve"
fi

# Future Crash owns its Tailscale Serve routes as one unit.  The reconciler
# touches only 7330/7331/7332 and never resets unrelated user Serve state.
# --yes is intentional: upgrades must replace stale backends without hanging on
# an interactive confirmation that an installer cannot answer.
if python3 "$ROOT/core/tailscale_serve.py"; then
  echo "  Tailscale Serve: Future Crash routes reconciled"
else
  echo "INSTALL ERROR: Future Crash Tailscale Serve routes are inconsistent" >&2
  echo "  No unrelated Tailscale Serve mappings were reset or removed." >&2
  exit 5
fi

# Verify the live daemon, not merely the files on disk. Upgrade lifecycle above
# guarantees that no previous Future Crash interpreter survives source replacement.
live_node_version() {
  python3 - <<'PY_NODE_VERSION' 2>/dev/null || true
import json, urllib.request
try:
    with urllib.request.urlopen("http://127.0.0.1:7332/v1/health", timeout=.35) as r:
        d=json.loads(r.read() or b"{}")
    print(str(d.get("version") or ""))
except Exception:
    pass
PY_NODE_VERSION
}

CLI_NODE_ERROR="$(mktemp)"
CLI_NODE_VERSION="$("$HOME/.local/bin/fcl-node" --version-number 2>"$CLI_NODE_ERROR" || true)"
if [[ "$CLI_NODE_VERSION" != "$EXPECTED_RELEASE" ]]; then
  echo "INSTALL ERROR: installed fcl-node reports '${CLI_NODE_VERSION:-unavailable}', expected $EXPECTED_RELEASE" >&2
  if [[ -s "$CLI_NODE_ERROR" ]]; then
    echo "  startup error:" >&2
    sed 's/^/    /' "$CLI_NODE_ERROR" >&2
  fi
  rm -f "$CLI_NODE_ERROR"
  exit 5
fi
rm -f "$CLI_NODE_ERROR"

INSTALLED_LOOK_VERSION="$("$HOME/.local/bin/lk" --version 2>/dev/null || true)"
case "$INSTALLED_LOOK_VERSION" in
  "LOOK $LOOK_SOURCE_VERSION · Future Crash + LOOK $EXPECTED_RELEASE") ;;
  *)
    echo "INSTALL ERROR: installed LOOK reports '${INSTALLED_LOOK_VERSION:-unavailable}'" >&2
    echo "  expected: LOOK $LOOK_SOURCE_VERSION · Future Crash + LOOK $EXPECTED_RELEASE" >&2
    exit 5
    ;;
esac

# A release is ready only when the process actually answering :7332 reports this
# exact release. This closes the old 'new files / old daemon' split-brain hole.
NODE_READY=0
for _ in {1..40}; do
  CURRENT_NODE_VERSION="$(live_node_version)"
  if [[ "$CURRENT_NODE_VERSION" == "$EXPECTED_RELEASE" ]]; then NODE_READY=1; break; fi
  sleep 0.2
done
if (( ! NODE_READY )); then
  echo "INSTALL ERROR: live Unified Node version '${CURRENT_NODE_VERSION:-unavailable}' does not match installed $EXPECTED_RELEASE" >&2
  if [[ "$(uname -s)" == "Darwin" ]]; then
    echo "  launchd state:" >&2
    launchctl print "gui/$(id -u)/com.futurecrash.look.node" >&2 2>/dev/null || true
    echo "  recent node log:" >&2
    tail -40 "$HOME/.local/share/future-crash-look/node.log" >&2 2>/dev/null || true
  else
    echo "  systemd state:" >&2
    systemctl --user status future-crash-look-node.service --no-pager >&2 2>/dev/null || true
  fi
  echo "  port owner:" >&2
  lsof -nP -iTCP:7332 -sTCP:LISTEN >&2 2>/dev/null || true
  exit 5
fi
# Verify Tailcat separately: node lockstep is not enough if launchd kept an old
# transport daemon or if its daemon PATH cannot discover Tailscale.
TAILCAT_CLI_VERSION="$(PYTHONPATH="$HOME/.local/share/future-crash-look/core${PYTHONPATH:+:$PYTHONPATH}" "$HOME/.local/bin/fcl-tailcat" --version 2>/dev/null || true)"
case "$TAILCAT_CLI_VERSION" in
  *" $EXPECTED_RELEASE") ;;
  *)
    echo "INSTALL ERROR: installed Tailcat reports '${TAILCAT_CLI_VERSION:-unavailable}', expected $EXPECTED_RELEASE" >&2
    exit 5
    ;;
esac

TAILCAT_READY_LIVE=0
for _ in {1..40}; do
  if python3 - <<PY_TAILCAT >/dev/null 2>&1
import json, socket
from pathlib import Path
expected="$EXPECTED_RELEASE"
with socket.create_connection(("127.0.0.1",7443),timeout=.35):
    pass
ad=json.loads((Path.home()/".config/future-crash-look/tailcat/advertisement.json").read_text())
assert str(ad.get("version") or "") == expected
assert all(".local.local:" not in str(x).casefold() for x in (ad.get("endpoints") or []))
PY_TAILCAT
  then TAILCAT_READY_LIVE=1; break; fi
  sleep 0.2
done
if (( ! TAILCAT_READY_LIVE )); then
  echo "INSTALL ERROR: live Tailcat :7443 / advertisement is not release $EXPECTED_RELEASE" >&2
  if [[ "$(uname -s)" == "Darwin" ]]; then
    launchctl print "gui/$(id -u)/com.futurecrash.look.tailcat" >&2 2>/dev/null || true
  else
    systemctl --user status future-crash-look-tailcat.service --no-pager >&2 2>/dev/null || true
  fi
  exit 5
fi

INGRESS_READY=0
for _ in {1..40}; do
  if python3 - <<'PY_CHECK' >/dev/null 2>&1
import json, urllib.request
with urllib.request.urlopen("http://127.0.0.1:7333/_fcl/metrics", timeout=1.0) as response:
    data = json.loads(response.read() or b"{}")
    assert response.status == 200
    assert data.get("ok") is True
PY_CHECK
  then
    INGRESS_READY=1
    break
  fi
  sleep 0.2
done
if (( ! INGRESS_READY )); then
  echo "INSTALL ERROR: Fabric ingress guard did not become ready on localhost :7333" >&2
  if [[ "$(uname -s)" == "Darwin" ]]; then
    echo "  launchd state:" >&2
    launchctl print "gui/$(id -u)/com.futurecrash.look.ingress" >&2 2>/dev/null || true
    echo "  recent ingress log:" >&2
    tail -40 "$HOME/.local/share/future-crash-look/ingress.log" >&2 2>/dev/null || true
  else
    echo "  systemd state:" >&2
    systemctl --user status future-crash-look-ingress.service --no-pager >&2 2>/dev/null || true
  fi
  echo "  port owner:" >&2
  lsof -nP -iTCP:7333 -sTCP:LISTEN >&2 2>/dev/null || true
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
if ! cmp -s "$ROOT/look/file_catalog.py" "$HOME/.local/share/look/file_catalog.py"; then
  echo "INSTALL ERROR: installed file catalog core does not match this checkout" >&2
  exit 5
fi
if ! cmp -s "$ROOT/look/media_watch.py" "$HOME/.local/share/look/media_watch.py"; then
  echo "INSTALL ERROR: installed removable media watcher does not match this checkout" >&2
  exit 5
fi
if ! cmp -s "$ROOT/look/media_core.py" "$HOME/.local/share/look/media_core.py"; then
  echo "INSTALL ERROR: installed media core does not match this checkout" >&2
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
if ! cmp -s "$ROOT/core/tailcat.py" "$HOME/.local/share/future-crash-look/core/tailcat.py"; then
  echo "INSTALL ERROR: installed Tailcat transport differs from release" >&2; exit 8
fi
if ! cmp -s "$ROOT/core/rendezvous.py" "$HOME/.local/share/future-crash-look/core/rendezvous.py"; then
  echo "INSTALL ERROR: installed Fabric rendezvous differs from release" >&2; exit 8
fi
if ! cmp -s "$ROOT/core/fabric_client.py" "$HOME/.local/share/future-crash-look/core/fabric_client.py"; then
  echo "INSTALL ERROR: Fabric client differs from release" >&2; exit 8
fi
if ! cmp -s "$ROOT/core/fabric_vision.py" "$HOME/.local/share/future-crash-look/core/fabric_vision.py"; then
  echo "INSTALL ERROR: installed Fabric Vision core differs from release" >&2; exit 8
fi
if ! cmp -s "$ROOT/core/fabric_identity.py" "$HOME/.local/share/future-crash-look/core/fabric_identity.py"; then
  echo "INSTALL ERROR: Fabric identity core differs from release" >&2; exit 8
fi
if ! cmp -s "$ROOT/core/endpoint_auth.py" "$HOME/.local/share/future-crash-look/core/endpoint_auth.py"; then
  echo "INSTALL ERROR: endpoint authorization core differs from release" >&2; exit 8
fi
if ! cmp -s "$ROOT/core/intent_normalizer.py" "$HOME/.local/share/future-crash-look/core/intent_normalizer.py"; then
  echo "INSTALL ERROR: intent normalizer differs from release" >&2; exit 8
fi
if ! cmp -s "$ROOT/core/jev.py" "$HOME/.local/share/future-crash-look/core/jev.py"; then
  echo "INSTALL ERROR: installed JEV core differs from release" >&2; exit 8
fi
if ! cmp -s "$ROOT/core/capability_curator.py" "$HOME/.local/share/future-crash-look/core/capability_curator.py"; then
  echo "INSTALL ERROR: installed capability curator differs from release" >&2; exit 8
fi
if ! cmp -s "$ROOT/core/fcl-openjev-worker" "$HOME/.local/bin/fcl-openjev-worker"; then
  echo "INSTALL ERROR: installed JEV-1 worker launcher differs from release" >&2; exit 8
fi
if ! cmp -s "$ROOT/core/conductor.py" "$HOME/.local/share/future-crash-look/core/conductor.py"; then
  echo "INSTALL ERROR: installed conductor differs from release" >&2; exit 8
fi
if ! cmp -s "$ROOT/core/memory_store.py" "$HOME/.local/share/future-crash-look/core/memory_store.py"; then
  echo "INSTALL ERROR: installed Fabric memory differs from release" >&2; exit 8
fi
if ! cmp -s "$ROOT/core/decision.py" "$HOME/.local/share/future-crash-look/core/decision.py"; then
  echo "INSTALL ERROR: installed Fabric decision plane differs from release" >&2; exit 8
fi
if ! cmp -s "$ROOT/core/cognition.py" "$HOME/.local/share/future-crash-look/core/cognition.py"; then
  echo "INSTALL ERROR: installed Fabric cognition core differs from release" >&2; exit 8
fi
if ! cmp -s "$ROOT/core/world_state.py" "$HOME/.local/share/future-crash-look/core/world_state.py"; then
  echo "INSTALL ERROR: installed typed world-state core differs from release" >&2; exit 8
fi
if ! cmp -s "$ROOT/core/live_state.py" "$HOME/.local/share/future-crash-look/core/live_state.py"; then
  echo "INSTALL ERROR: installed live-state core differs from release" >&2; exit 8
fi
if ! cmp -s "$ROOT/core/observation.py" "$HOME/.local/share/future-crash-look/core/observation.py"; then
  echo "INSTALL ERROR: installed observation plane differs from release" >&2; exit 8
fi
if ! PYTHONPATH="$HOME/.local/share/future-crash-look/core" python3 - <<'PY_RUNTIME' >/dev/null 2>&1
import conductor, fabric_client, memory_store, decision, cognition, world_state, live_state
import observation
import fabric_identity, endpoint_auth, intent_normalizer, tailcat, rendezvous
import jev, capability_curator
assert conductor.classify("ping").tier == "reflex"
assert callable(fabric_client.stream_infer)
assert callable(fabric_identity.public_identity)
assert callable(endpoint_auth.EndpointAuth)
assert intent_normalizer.normalize("play any movie")["kind"] == "video"
assert callable(jev.command_imperative)
assert callable(capability_curator.refresh)
assert "capability.catalog" in capability_curator.public_capabilities()
assert callable(tailcat.ensure_identity)
assert callable(rendezvous.sync_once)
assert callable(world_state.WorldState)
assert callable(live_state.snapshot)
assert decision.plan(profile="power", confidence=.7).timeout_action == "continue"
assert cognition.analyze("headlienes", use_openjev=False).primary == "web"
assert any(row["id"] == "audio.speak" for row in cognition.public_registry())
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

# Reconcile the local catalog in the background. Scans are single-writer and
# content extraction is incremental, so upgrades can safely seed new index layers.
( nohup "$HOME/.local/bin/lk" scan >"$HOME/.local/share/look/file-scan.log" 2>&1 & ) || true
echo "  file/content catalog reconciliation started in background"

echo "  fcl-node identity   # stable Fabric node identity"
echo "  fcl-tailcat show    # native encrypted transport endpoints"
echo "  lk fabric rendezvous status  # optional public discovery state"
echo "  fcl-node pair-code  # open a one-use pairing invitation"
echo "  fcl-node fabric     # human view of the compute fabric"
echo "  fcl-node models     # model capability advertisements"
echo "  fcl-node pulse      # shared heartbeat"
echo "  fcl-node activity   # supervisor truth"
echo "  fcl-node http       # local + guarded-ingress HTTP pressure"
echo "  fcl-node nodes      # peers + node advertisements"
echo "  fcl-node jobs       # durable Fabric work ledger"

# All verification completed; failure recovery is no longer needed.
INSTALL_COMPLETE=1
trap - EXIT
