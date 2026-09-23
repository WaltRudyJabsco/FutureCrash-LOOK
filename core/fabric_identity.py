#!/usr/bin/env python3
"""Accountless Fabric node identity, trust store, and one-time pairing.

Identity is local and transport-independent. Tailscale/LAN may carry pairing traffic,
but neither supplies the node's identity or trust decision.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
import shutil
import socket
import struct
import subprocess
import tempfile
import time
import urllib.parse
import urllib.request
from pathlib import Path

SCHEMA = "fabric-identity-v1"
PAIR_SCHEMA = "fabric-pair-v1"
PAIR_TTL_SECONDS = 300
PAIR_CODE_BYTES = 10  # 80 bits; short enough to type, strong enough for a 5-minute invitation.


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


def _public_key_parts(text: str) -> tuple[str, str]:
    parts = str(text or "").strip().split()
    if len(parts) < 2 or parts[0] != "ssh-ed25519":
        raise ValueError("Fabric identity requires an ssh-ed25519 public key")
    # Validate encoding so malformed trust records cannot become identities.
    base64.b64decode(parts[1].encode("ascii"), validate=True)
    return parts[0], parts[1]


def public_identity(public_key: str, *, name: str = "", hostname: str = "") -> dict:
    algorithm, body = _public_key_parts(public_key)
    digest = hashlib.sha256(body.encode("ascii")).digest()
    node_id = "fcl-" + digest.hex()[:24]
    short = base64.b32encode(digest[:10]).decode("ascii").rstrip("=")
    fingerprint = "-".join(short[i:i+4] for i in range(0, len(short), 4))
    return {
        "schema": SCHEMA,
        "node_id": node_id,
        "fingerprint": fingerprint,
        "algorithm": algorithm,
        "public_key": f"{algorithm} {body}",
        "name": str(name or hostname or socket.gethostname()),
        "hostname": str(hostname or socket.gethostname()),
    }


def format_pair_code(raw: bytes | None = None) -> str:
    token = base64.b32encode(raw or secrets.token_bytes(PAIR_CODE_BYTES)).decode("ascii").rstrip("=")
    return "-".join(token[i:i+4] for i in range(0, len(token), 4))


def normalize_pair_code(code: str) -> str:
    return "".join(ch for ch in str(code or "").upper() if ch.isalnum())


class FabricIdentity:
    def __init__(self, root: Path | None = None):
        self.root = Path(root or (Path.home() / ".config/future-crash-look/identity"))
        self.private_key = self.root / "node_ed25519"
        self.public_key = self.root / "node_ed25519.pub"
        self.trust_path = self.root / "trust.json"
        self.pair_path = self.root / "pairing.json"

    def ensure(self) -> dict:
        self.root.mkdir(parents=True, exist_ok=True)
        try:
            self.root.chmod(0o700)
        except OSError:
            pass
        if not (self.private_key.exists() and self.public_key.exists()):
            ssh_keygen = shutil.which("ssh-keygen")
            if ssh_keygen:
                proc = subprocess.run(
                    [ssh_keygen, "-q", "-t", "ed25519", "-N", "", "-C", "future-crash-look", "-f", str(self.private_key)],
                    text=True, capture_output=True, timeout=15,
                )
                if proc.returncode:
                    raise RuntimeError((proc.stderr or proc.stdout or "ssh-keygen failed").strip())
            else:
                # OpenSSL is the dependency-light fallback used on minimal Unix installs.
                # Convert its standard Ed25519 SubjectPublicKeyInfo into OpenSSH public form
                # so node IDs stay identical regardless of which key generator was present.
                openssl = shutil.which("openssl")
                if not openssl:
                    raise RuntimeError("ssh-keygen or openssl is required to create a Fabric identity")
                proc = subprocess.run([openssl, "genpkey", "-algorithm", "ED25519", "-out", str(self.private_key)],
                                      text=True, capture_output=True, timeout=15)
                if proc.returncode:
                    raise RuntimeError((proc.stderr or proc.stdout or "openssl Ed25519 generation failed").strip())
                pub = subprocess.run([openssl, "pkey", "-in", str(self.private_key), "-pubout", "-outform", "DER"],
                                     capture_output=True, timeout=15)
                if pub.returncode or len(pub.stdout) < 32:
                    raise RuntimeError((pub.stderr.decode("utf-8","replace") if pub.stderr else "openssl public-key export failed").strip())
                raw = pub.stdout[-32:]
                alg = b"ssh-ed25519"
                blob = struct.pack(">I", len(alg)) + alg + struct.pack(">I", len(raw)) + raw
                self.public_key.write_text("ssh-ed25519 " + base64.b64encode(blob).decode("ascii") + " future-crash-look\n", encoding="utf-8")
        try:
            self.private_key.chmod(0o600)
            self.public_key.chmod(0o644)
        except OSError:
            pass
        return self.public()

    def public(self, *, name: str = "", hostname: str = "") -> dict:
        if not self.public_key.exists():
            self.ensure()
        return public_identity(self.public_key.read_text(encoding="utf-8"), name=name, hostname=hostname)

    def trusted(self) -> dict:
        data = _load_json(self.trust_path, {"schema": SCHEMA, "nodes": {}})
        nodes = data.get("nodes") if isinstance(data.get("nodes"), dict) else {}
        return {"schema": SCHEMA, "nodes": nodes}

    def trust(self, peer: dict, *, source: str = "pairing") -> dict:
        if not isinstance(peer, dict):
            raise ValueError("peer identity must be an object")
        canonical = public_identity(
            str(peer.get("public_key") or ""),
            name=str(peer.get("name") or ""),
            hostname=str(peer.get("hostname") or ""),
        )
        claimed = str(peer.get("node_id") or "")
        if claimed and claimed != canonical["node_id"]:
            raise ValueError("peer node_id does not match its public key")
        data = self.trusted()
        record = dict(canonical)
        record.update({"trusted_at": _now(), "source": str(source or "pairing")})
        data["nodes"][canonical["node_id"]] = record
        _atomic_json(self.trust_path, data)
        return record

    def untrust(self, node_id: str) -> bool:
        data = self.trusted()
        removed = data["nodes"].pop(str(node_id or ""), None) is not None
        if removed:
            _atomic_json(self.trust_path, data)
        return removed

    def start_pairing(self, endpoint: str, *, name: str = "", hostname: str = "", ttl: int = PAIR_TTL_SECONDS) -> dict:
        me = self.ensure()
        if name or hostname:
            me = self.public(name=name, hostname=hostname)
        endpoint = str(endpoint or "").rstrip("/")
        if not endpoint.startswith(("http://", "https://")):
            raise ValueError("pairing endpoint must be http:// or https://")
        code = format_pair_code()
        expires = _now() + max(60, min(int(ttl), 900))
        state = {
            "schema": PAIR_SCHEMA,
            "code_hash": hashlib.sha256(normalize_pair_code(code).encode("ascii")).hexdigest(),
            "created": _now(), "expires": expires, "endpoint": endpoint,
        }
        _atomic_json(self.pair_path, state)
        query = urllib.parse.urlencode({"v": "1", "url": endpoint, "code": code, "node": me["node_id"]})
        return {"schema": PAIR_SCHEMA, "identity": me, "code": code, "endpoint": endpoint,
                "expires": expires, "uri": "fcl://pair?" + query}

    def accept_pairing(self, code: str, peer: dict) -> dict:
        state = _load_json(self.pair_path, {})
        if state.get("schema") != PAIR_SCHEMA:
            raise ValueError("no pairing invitation is open")
        if float(state.get("expires") or 0) < _now():
            try: self.pair_path.unlink()
            except OSError: pass
            raise ValueError("pairing invitation expired")
        supplied = hashlib.sha256(normalize_pair_code(code).encode("ascii")).hexdigest()
        if not secrets.compare_digest(str(state.get("code_hash") or ""), supplied):
            raise ValueError("pairing code is invalid")
        record = self.trust(peer, source="pairing")
        # Invitations are one-use capabilities. Consume before answering success.
        try: self.pair_path.unlink()
        except OSError: pass
        return record

    def pairing_status(self) -> dict:
        state = _load_json(self.pair_path, {})
        if not state or float(state.get("expires") or 0) < _now():
            return {"open": False}
        return {"open": True, "endpoint": state.get("endpoint"), "expires": state.get("expires")}


def parse_pair_target(value: str, code: str | None = None) -> tuple[str, str]:
    value = str(value or "").strip()
    if value.startswith("fcl://pair?"):
        q = urllib.parse.parse_qs(urllib.parse.urlparse(value).query)
        endpoint = str((q.get("url") or [""])[0]).rstrip("/")
        pair_code = str((q.get("code") or [""])[0])
        if not endpoint or not pair_code:
            raise ValueError("pairing URI is incomplete")
        return endpoint, pair_code
    if not code:
        raise ValueError("pairing requires ENDPOINT CODE or an fcl://pair URI")
    return value.rstrip("/"), str(code)


def join_pairing(local: FabricIdentity, target: str, code: str | None = None, *, name: str = "", hostname: str = "", timeout: float = 6.0) -> dict:
    endpoint, pair_code = parse_pair_target(target, code)
    me = local.ensure()
    if name or hostname:
        me = local.public(name=name, hostname=hostname)
    body = json.dumps({"schema": PAIR_SCHEMA, "code": pair_code, "identity": me}, separators=(",", ":")).encode()
    req = urllib.request.Request(endpoint + "/v1/identity/pair", data=body, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            result = json.loads(response.read() or b"{}")
    except Exception as exc:
        raise RuntimeError(f"pairing failed: {exc}") from exc
    remote = result.get("identity") if isinstance(result, dict) else None
    if not isinstance(remote, dict):
        raise RuntimeError(str((result or {}).get("error") or "pairing response had no identity"))
    stored = local.trust(remote, source="pairing")
    return {"ok": True, "peer": stored, "remote": remote}


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=["init", "show", "trust"])
    a = ap.parse_args()
    store = FabricIdentity()
    if a.command in {"init", "show"}:
        print(json.dumps(store.ensure(), indent=2))
    else:
        print(json.dumps(store.trusted(), indent=2))
