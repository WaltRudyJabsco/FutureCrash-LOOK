#!/usr/bin/env python3
"""Fabric rendezvous: tiny public presence registry for already-trusted nodes.

Rendezvous is deliberately not identity, authorization, or payload transport.  A
paired node derives an opaque lookup slot from the pairwise authorization token it
already shares with one peer.  Presence is signed by the node's existing Ed25519
identity.  The public service therefore learns only ephemeral network presence and
cannot create Fabric trust.

6.7.2 is the first stage of replacing Tailscale discovery.  It does not yet perform
UDP hole punching or encrypted relay; Tailcat/Tailscale remain the data transports.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import socket
import subprocess
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

try:
    from .fabric_identity import FabricIdentity, public_identity
except ImportError:
    from fabric_identity import FabricIdentity, public_identity

VERSION = "6.7.6"
RELEASE_NAME = "HOME BASE"
PRESENCE_SCHEMA = "fabric-rendezvous-presence-v1"
RESPONSE_SCHEMA = "fabric-rendezvous-response-v1"
SIGN_NAMESPACE = "future-crash-look-rendezvous"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 7788
DEFAULT_TTL_SECONDS = 90
MAX_TTL_SECONDS = 180
MAX_CLOCK_SKEW_SECONDS = 120
MAX_SLOTS = 64
SYNC_INTERVAL_SECONDS = 45
CONFIG_PATH = Path.home() / ".config/future-crash-look/rendezvous.json"
STATE_PATH = Path.home() / ".config/future-crash-look/rendezvous-state.json"
_SLOT_RE = re.compile(r"^[0-9a-f]{64}$")


def _now() -> float:
    return time.time()


def _atomic_json(path: Path, data: dict, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=path.name + ".", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, sort_keys=True)
            fh.write("\n")
        os.chmod(tmp_name, mode)
        os.replace(tmp_name, path)
    finally:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass


def _load_json(path: Path, default: dict) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else dict(default)
    except Exception:
        return dict(default)


def load_config() -> dict:
    data = _load_json(CONFIG_PATH, {})
    url = str(data.get("url") or os.getenv("FCL_RENDEZVOUS_URL") or "").rstrip("/")
    enabled = bool(data.get("enabled", bool(url)))
    return {"enabled": enabled and bool(url), "url": url}


def save_config(url: str | None) -> dict:
    url = str(url or "").strip().rstrip("/")
    if url and not url.startswith(("http://", "https://")):
        raise ValueError("rendezvous URL must be http:// or https://")
    data = {"enabled": bool(url), "url": url, "updated_at": _now()}
    _atomic_json(CONFIG_PATH, data)
    return data


def derive_slot(auth_token: str) -> str:
    token = str(auth_token or "")
    if len(token) < 32:
        raise ValueError("trusted peer has no usable authorization token")
    # The pairwise token never crosses the network.  The beacon sees only this
    # one-way capability label, different from Fabric's normal auth-token hash.
    return hashlib.sha256(("fabric-rendezvous-slot-v1\0" + token).encode("utf-8")).hexdigest()


def canonical_bytes(payload: dict) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def signer_available() -> bool:
    return bool(shutil.which("ssh-keygen"))


def _tailcat_advertisement() -> dict:
    path = Path.home() / ".config/future-crash-look/tailcat/advertisement.json"
    return _load_json(path, {})


def build_presence(identity: FabricIdentity, *, now_value: float | None = None, ttl: int = DEFAULT_TTL_SECONDS) -> dict:
    me = identity.ensure()
    trust = identity.trusted()
    slots = []
    for row in (trust.get("nodes") or {}).values():
        if not isinstance(row, dict):
            continue
        token = str(row.get("auth_token") or "")
        if len(token) < 32:
            continue
        try:
            slots.append(derive_slot(token))
        except ValueError:
            continue
    slots = sorted(set(slots))[:MAX_SLOTS]
    tc = _tailcat_advertisement()
    issued = int(now_value if now_value is not None else _now())
    ttl = max(30, min(int(ttl), MAX_TTL_SECONDS))
    endpoints = [str(x).rstrip("/") for x in (tc.get("endpoints") or []) if str(x).startswith("https://")]
    return {
        "schema": PRESENCE_SCHEMA,
        "version": VERSION,
        "node_id": me["node_id"],
        "public_key": me["public_key"],
        "name": me.get("name") or "",
        "hostname": me.get("hostname") or "",
        "issued_at": issued,
        "expires_at": issued + ttl,
        "tailcat_port": int(tc.get("port") or 7443),
        "tailcat_endpoints": endpoints[:16],
        "slots": slots,
    }


def sign_payload(identity: FabricIdentity, payload: dict) -> str:
    ssh_keygen = shutil.which("ssh-keygen")
    if not ssh_keygen:
        raise RuntimeError("rendezvous signing requires ssh-keygen")
    identity.ensure()
    raw = canonical_bytes(payload)
    with tempfile.TemporaryDirectory(prefix="fcl-rendezvous-sign-") as td:
        message = Path(td) / "presence.json"
        message.write_bytes(raw)
        proc = subprocess.run(
            [ssh_keygen, "-Y", "sign", "-f", str(identity.private_key), "-n", SIGN_NAMESPACE, str(message)],
            capture_output=True, text=True, timeout=8,
        )
        if proc.returncode:
            raise RuntimeError((proc.stderr or proc.stdout or "ssh-keygen signing failed").strip())
        sig_path = Path(str(message) + ".sig")
        if not sig_path.exists():
            raise RuntimeError("ssh-keygen did not produce a rendezvous signature")
        return sig_path.read_text(encoding="utf-8")


def verify_presence(payload: dict, signature: str, *, now_value: float | None = None) -> dict:
    if not isinstance(payload, dict) or payload.get("schema") != PRESENCE_SCHEMA:
        raise ValueError("invalid rendezvous presence schema")
    canonical = public_identity(str(payload.get("public_key") or ""), name=str(payload.get("name") or ""), hostname=str(payload.get("hostname") or ""))
    if canonical["node_id"] != str(payload.get("node_id") or ""):
        raise ValueError("rendezvous node_id does not match public key")
    issued = int(payload.get("issued_at") or 0)
    expires = int(payload.get("expires_at") or 0)
    now_int = int(now_value if now_value is not None else _now())
    if issued > now_int + MAX_CLOCK_SKEW_SECONDS or issued < now_int - (MAX_TTL_SECONDS + MAX_CLOCK_SKEW_SECONDS):
        raise ValueError("rendezvous presence timestamp is outside the accepted window")
    if expires <= now_int or expires - issued > MAX_TTL_SECONDS or expires <= issued:
        raise ValueError("rendezvous presence has invalid expiry")
    slots = payload.get("slots") or []
    if not isinstance(slots, list) or len(slots) > MAX_SLOTS or any(not _SLOT_RE.match(str(x)) for x in slots):
        raise ValueError("rendezvous presence contains invalid slots")
    ssh_keygen = shutil.which("ssh-keygen")
    if not ssh_keygen:
        raise RuntimeError("rendezvous verification requires ssh-keygen")
    with tempfile.TemporaryDirectory(prefix="fcl-rendezvous-verify-") as td:
        td = Path(td)
        allowed = td / "allowed_signers"
        message_sig = td / "presence.sig"
        # Identity is derived from this exact public key before verification.
        allowed.write_text(f"{canonical['node_id']} {canonical['public_key']}\n", encoding="utf-8")
        message_sig.write_text(str(signature or ""), encoding="utf-8")
        proc = subprocess.run(
            [ssh_keygen, "-Y", "verify", "-f", str(allowed), "-I", canonical["node_id"], "-n", SIGN_NAMESPACE, "-s", str(message_sig)],
            input=canonical_bytes(payload), capture_output=True, timeout=8,
        )
        if proc.returncode:
            detail = (proc.stderr or proc.stdout or b"signature verification failed").decode("utf-8", "replace").strip()
            raise ValueError(detail or "rendezvous signature verification failed")
    return canonical


def _urlopen_json(req: urllib.request.Request | str, *, timeout: float = 4.0) -> dict:
    with urllib.request.urlopen(req, timeout=timeout) as response:
        data = json.loads(response.read() or b"{}")
    if not isinstance(data, dict):
        raise RuntimeError("rendezvous returned invalid JSON")
    return data


def announce(identity: FabricIdentity, url: str, *, timeout: float = 4.0) -> dict:
    payload = build_presence(identity)
    if not payload["slots"]:
        return {"ok": True, "announced": 0, "reason": "no authorized peers"}
    signature = sign_payload(identity, payload)
    body = json.dumps({"payload": payload, "signature": signature}, separators=(",", ":")).encode("utf-8")
    req = urllib.request.Request(url.rstrip("/") + "/v1/presence", data=body, headers={"Content-Type": "application/json"}, method="POST")
    result = _urlopen_json(req, timeout=timeout)
    if not result.get("ok"):
        raise RuntimeError(str(result.get("error") or "rendezvous announce failed"))
    return result


def resolve(identity: FabricIdentity, url: str, *, timeout: float = 4.0) -> dict:
    trust = identity.trusted()
    resolved = []
    errors = []
    for expected_id, row in (trust.get("nodes") or {}).items():
        if not isinstance(row, dict):
            continue
        token = str(row.get("auth_token") or "")
        if len(token) < 32:
            continue
        try:
            slot = derive_slot(token)
            query = urllib.parse.urlencode({"slot": slot})
            result = _urlopen_json(url.rstrip("/") + "/v1/resolve?" + query, timeout=timeout)
            hits = result.get("nodes") or []
            match = next((x for x in hits if isinstance(x, dict) and str((x.get("payload") or {}).get("node_id") or "") == expected_id), None)
            if not match:
                continue
            payload = match.get("payload") or {}
            verify_presence(payload, str(match.get("signature") or ""))
            candidates = []
            observed = str(match.get("observed_endpoint") or "")
            if observed.startswith("https://"):
                candidates.append(observed.rstrip("/"))
            # LAN addresses are harmless candidates and useful when a public beacon
            # is also reachable from machines on different local interfaces.
            candidates.extend(str(x).rstrip("/") for x in (payload.get("tailcat_endpoints") or []) if str(x).startswith("https://"))
            candidates = list(dict.fromkeys(candidates))
            identity.learn_discovered_endpoints(expected_id, candidates, expires_at=float(payload.get("expires_at") or 0), source="rendezvous")
            resolved.append({"node_id": expected_id, "name": row.get("name") or expected_id, "candidates": candidates})
        except Exception as exc:
            errors.append({"node_id": expected_id, "error": str(exc)[:240]})
    return {"ok": not errors, "resolved": resolved, "errors": errors}


def sync_once(identity: FabricIdentity | None = None) -> dict:
    identity = identity or FabricIdentity()
    cfg = load_config()
    if not cfg.get("enabled"):
        state = {"enabled": False, "url": cfg.get("url") or "", "updated_at": _now()}
        _atomic_json(STATE_PATH, state)
        return state
    state = {"enabled": True, "url": cfg["url"], "updated_at": _now(), "announce": None, "resolve": None, "error": None}
    try:
        state["announce"] = announce(identity, cfg["url"])
        state["resolve"] = resolve(identity, cfg["url"])
    except Exception as exc:
        state["error"] = str(exc)[:300]
    _atomic_json(STATE_PATH, state)
    return state


def background_loop(identity: FabricIdentity | None = None, *, interval: float = SYNC_INTERVAL_SECONDS) -> None:
    identity = identity or FabricIdentity()
    while True:
        try:
            if load_config().get("enabled"):
                sync_once(identity)
        except Exception:
            pass
        time.sleep(max(15.0, float(interval)))


def status() -> dict:
    cfg = load_config()
    state = _load_json(STATE_PATH, {})
    return {
        "version": VERSION,
        "enabled": bool(cfg.get("enabled")),
        "url": cfg.get("url") or "",
        "signer": signer_available(),
        "last_sync": state,
    }


class Registry:
    """Ephemeral capability-slot registry. Restarting the beacon simply empties it."""
    def __init__(self):
        self.lock = threading.RLock()
        self.slots: dict[str, dict[str, dict]] = {}

    def put(self, payload: dict, signature: str, observed_ip: str) -> int:
        verify_presence(payload, signature)
        port = int(payload.get("tailcat_port") or 7443)
        observed_endpoint = _https_endpoint(observed_ip, port)
        record = {"payload": payload, "signature": signature, "observed_endpoint": observed_endpoint, "seen_at": _now()}
        count = 0
        with self.lock:
            self._prune_locked()
            for slot in payload.get("slots") or []:
                self.slots.setdefault(slot, {})[payload["node_id"]] = record
                count += 1
        return count

    def get(self, slot: str) -> list[dict]:
        if not _SLOT_RE.match(str(slot or "")):
            return []
        with self.lock:
            self._prune_locked()
            return [dict(x) for x in (self.slots.get(slot) or {}).values()]

    def _prune_locked(self) -> None:
        now_value = _now()
        dead_slots = []
        for slot, rows in self.slots.items():
            for node_id in list(rows):
                payload = rows[node_id].get("payload") or {}
                if float(payload.get("expires_at") or 0) <= now_value:
                    rows.pop(node_id, None)
            if not rows:
                dead_slots.append(slot)
        for slot in dead_slots:
            self.slots.pop(slot, None)


REGISTRY = Registry()


def _https_endpoint(host: str, port: int) -> str:
    host = str(host or "").strip()
    if not host:
        return ""
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"
    return f"https://{host}:{int(port)}"


class Handler(BaseHTTPRequestHandler):
    server_version = "FCLRendezvous/6.7.6"

    def log_message(self, fmt, *args):
        return

    def _json(self, code: int, data: dict) -> None:
        body = json.dumps(data, separators=(",", ":")).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/health":
            self._json(200, {"ok": True, "service": "fabric-rendezvous", "version": VERSION}); return
        if parsed.path == "/v1/resolve":
            slot = str((urllib.parse.parse_qs(parsed.query).get("slot") or [""])[0])
            if not _SLOT_RE.match(slot):
                self._json(400, {"ok": False, "error": "invalid slot"}); return
            self._json(200, {"ok": True, "schema": RESPONSE_SCHEMA, "nodes": REGISTRY.get(slot)}); return
        self._json(404, {"ok": False, "error": "not found"})

    def do_POST(self):
        if urllib.parse.urlparse(self.path).path != "/v1/presence":
            self._json(404, {"ok": False, "error": "not found"}); return
        try:
            size = int(self.headers.get("Content-Length") or 0)
            if size <= 0 or size > 256 * 1024:
                raise ValueError("invalid request size")
            data = json.loads(self.rfile.read(size) or b"{}")
            payload = data.get("payload") if isinstance(data, dict) else None
            signature = str(data.get("signature") or "") if isinstance(data, dict) else ""
            if not isinstance(payload, dict) or not signature:
                raise ValueError("presence requires payload and signature")
            count = REGISTRY.put(payload, signature, self.client_address[0])
            self._json(200, {"ok": True, "accepted_slots": count, "expires_at": payload.get("expires_at")})
        except Exception as exc:
            self._json(400, {"ok": False, "error": str(exc)[:300]})


def serve(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> int:
    if not signer_available():
        raise RuntimeError("rendezvous service requires ssh-keygen for Ed25519 verification")
    server = ThreadingHTTPServer((host, int(port)), Handler)
    print(f"Future Crash + LOOK rendezvous {VERSION} · {RELEASE_NAME} · http://{host}:{port}", flush=True)
    try:
        server.serve_forever(poll_interval=.25)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Future Crash + LOOK Fabric rendezvous")
    ap.add_argument("command", nargs="?", default="status", choices=["status", "serve", "set", "off", "announce", "resolve", "sync"])
    ap.add_argument("value", nargs="?")
    ap.add_argument("--host", default=DEFAULT_HOST)
    ap.add_argument("--port", type=int, default=DEFAULT_PORT)
    ap.add_argument("--version", action="version", version=f"Future Crash + LOOK rendezvous {VERSION} · {RELEASE_NAME}")
    a = ap.parse_args()
    identity = FabricIdentity()
    if a.command == "serve":
        return serve(a.host, a.port)
    if a.command == "set":
        if not a.value:
            ap.error("set requires URL")
        print(json.dumps(save_config(a.value), indent=2)); return 0
    if a.command == "off":
        print(json.dumps(save_config(None), indent=2)); return 0
    if a.command == "announce":
        cfg = load_config(); url = str(a.value or cfg.get("url") or "")
        if not url: ap.error("announce requires configured rendezvous URL")
        print(json.dumps(announce(identity, url), indent=2)); return 0
    if a.command == "resolve":
        cfg = load_config(); url = str(a.value or cfg.get("url") or "")
        if not url: ap.error("resolve requires configured rendezvous URL")
        print(json.dumps(resolve(identity, url), indent=2)); return 0
    if a.command == "sync":
        print(json.dumps(sync_once(identity), indent=2)); return 0
    print(json.dumps(status(), indent=2)); return 0


if __name__ == "__main__":
    raise SystemExit(main())
