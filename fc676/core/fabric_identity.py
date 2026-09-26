#!/usr/bin/env python3
"""Accountless Fabric node identity, trust, pairing, and peer authorization.

Fabric identity is transport-independent. Tailscale/LAN may carry packets, but
Fabric owns who a peer is and whether that peer is authorized.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
import shutil
import socket
import ssl
import struct
import subprocess
import tempfile
import time
import urllib.parse
import urllib.request
from pathlib import Path

SCHEMA = "fabric-identity-v2"
PAIR_SCHEMA = "fabric-pair-v2"
PAIR_TTL_SECONDS = 300
PAIR_MAX_ATTEMPTS = 8
AUTH_TOKEN_BYTES = 32


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


def format_pair_code() -> str:
    # Eight decimal digits are comfortable to read/message while a five-minute,
    # one-use invitation plus attempt limiting keeps the online guessing surface small.
    return f"{secrets.randbelow(100_000_000):08d}"


def normalize_pair_code(code: str) -> str:
    return "".join(ch for ch in str(code or "") if ch.isdigit())


def _new_auth_token() -> str:
    return secrets.token_urlsafe(AUTH_TOKEN_BYTES)


def _token_hash(token: str) -> str:
    return hashlib.sha256(str(token or "").encode("utf-8")).hexdigest()


def _host(value: str) -> str:
    try:
        return (urllib.parse.urlparse(value).hostname or "").casefold()
    except Exception:
        return ""


def _tailcat_advertisement() -> dict:
    path = Path.home() / ".config/future-crash-look/tailcat/advertisement.json"
    try:
        data=json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data,dict) else {}
    except Exception:
        return {}


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

    def trusted(self, *, public: bool = False) -> dict:
        data = _load_json(self.trust_path, {"schema": SCHEMA, "nodes": {}})
        nodes = data.get("nodes") if isinstance(data.get("nodes"), dict) else {}
        if not public:
            return {"schema": SCHEMA, "nodes": nodes}
        clean = {}
        for node_id, row in nodes.items():
            if not isinstance(row, dict):
                continue
            clean[node_id] = {k:v for k,v in row.items() if k not in {"auth_token","auth_token_hash"}}
            clean[node_id]["authorized"] = bool(row.get("auth_token_hash"))
        return {"schema": SCHEMA, "nodes": clean}

    def trust(self, peer: dict, *, source: str = "pairing", auth_token: str | None = None,
              endpoint: str | None = None) -> dict:
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
        prior = dict((data.get("nodes") or {}).get(canonical["node_id"]) or {})
        record = dict(canonical)
        record.update({"trusted_at": prior.get("trusted_at") or _now(), "updated_at": _now(), "source": str(source or "pairing")})
        transports = peer.get("transports") if isinstance(peer.get("transports"),dict) else prior.get("transports")
        if isinstance(transports,dict) and transports:
            record["transports"] = transports
        token = str(auth_token or prior.get("auth_token") or "")
        if token:
            record["auth_token"] = token
            record["auth_token_hash"] = _token_hash(token)
        if endpoint:
            record["endpoint"] = str(endpoint).rstrip("/")
        elif prior.get("endpoint"):
            record["endpoint"] = prior["endpoint"]
        data["schema"] = SCHEMA
        data.setdefault("nodes", {})[canonical["node_id"]] = record
        _atomic_json(self.trust_path, data)
        return record

    def untrust(self, node_id: str) -> bool:
        data = self.trusted()
        removed = data["nodes"].pop(str(node_id or ""), None) is not None
        if removed:
            _atomic_json(self.trust_path, data)
        return removed

    def learn_discovered_endpoints(self, node_id: str, endpoints: list[str], *, expires_at: float, source: str = "rendezvous") -> bool:
        """Attach short-lived address candidates to an already-trusted peer.

        Discovery may tell us where a peer is, but it never gets to change who
        that peer is or which Tailcat certificate was pinned during pairing.
        """
        data = self.trusted()
        row = (data.get("nodes") or {}).get(str(node_id or ""))
        if not isinstance(row, dict):
            return False
        transports = row.setdefault("transports", {})
        tailcat = transports.setdefault("tailcat", {})
        clean = []
        for value in endpoints or []:
            value = str(value or "").rstrip("/")
            if value.startswith("https://") and value not in clean:
                clean.append(value)
        tailcat["discovered_endpoints"] = clean[:16]
        tailcat["discovered_expires"] = float(expires_at or 0)
        tailcat["discovered_source"] = str(source or "discovery")
        row["updated_at"] = _now()
        _atomic_json(self.trust_path, data)
        return True

    @staticmethod
    def _active_tailcat_endpoints(row: dict, *, now_value: float | None = None) -> list[str]:
        tc = ((row.get("transports") or {}).get("tailcat") or {}) if isinstance(row.get("transports"), dict) else {}
        values = [str(x).rstrip("/") for x in (tc.get("endpoints") or []) if str(x).startswith("https://")]
        current = float(now_value if now_value is not None else _now())
        if float(tc.get("discovered_expires") or 0) > current:
            values.extend(str(x).rstrip("/") for x in (tc.get("discovered_endpoints") or []) if str(x).startswith("https://"))
        return list(dict.fromkeys(values))

    def verify_peer(self, node_id: str, token: str) -> bool:
        row = (self.trusted().get("nodes") or {}).get(str(node_id or "")) or {}
        expected = str(row.get("auth_token_hash") or "")
        if not expected or not token:
            return False
        return secrets.compare_digest(expected, _token_hash(token))

    def auth_headers_for_url(self, url: str) -> dict:
        row=self._matching_trust_row(url)
        token=str((row or {}).get("auth_token") or "")
        if not token: return {}
        me=self.ensure()
        return {"X-Fabric-Node":me["node_id"],"Authorization":"Bearer "+token}

    def _matching_trust_row(self, url: str) -> dict | None:
        target=_host(url)
        if not target: return None
        for row in (self.trusted().get("nodes") or {}).values():
            if not isinstance(row,dict): continue
            candidates={_host(str(row.get("endpoint") or "")), str(row.get("hostname") or "").casefold(), str(row.get("name") or "").casefold()}
            for ep in self._active_tailcat_endpoints(row):
                candidates.add(_host(str(ep)))
            candidates.discard("")
            if target in candidates or any(target.split(".",1)[0] == c.split(".",1)[0] for c in candidates):
                return row
        return None

    def ssl_context_for_url(self, url: str):
        row=self._matching_trust_row(url)
        if not row: return None
        tc=((row.get("transports") or {}).get("tailcat") or {}) if isinstance(row.get("transports"),dict) else {}
        cert=str(tc.get("cert_pem") or "")
        endpoints=self._active_tailcat_endpoints(row)
        target=_host(url)
        if not cert or target not in {_host(x) for x in endpoints}:
            return None
        ctx=ssl.create_default_context(cadata=cert)
        # Exact pinned certificate learned during authenticated pairing is the
        # identity check; its CN intentionally does not depend on DHCP addresses.
        ctx.check_hostname=False
        return ctx

    def local_transports(self) -> dict:
        tc=_tailcat_advertisement()
        return {"tailcat":tc} if tc else {}

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
            "created": _now(), "expires": expires, "endpoint": endpoint, "attempts": 0,
        }
        _atomic_json(self.pair_path, state)
        query = urllib.parse.urlencode({"v": "2", "url": endpoint, "code": code, "node": me["node_id"]})
        return {"schema": PAIR_SCHEMA, "identity": me, "code": code, "endpoint": endpoint,
                "expires": expires, "uri": "fcl://pair?" + query}

    def accept_pairing(self, code: str, peer: dict, *, auth_token: str, peer_endpoint: str | None = None) -> dict:
        state = _load_json(self.pair_path, {})
        if state.get("schema") not in {PAIR_SCHEMA, "fabric-pair-v1"}:
            raise ValueError("no pairing invitation is open")
        if float(state.get("expires") or 0) < _now():
            try: self.pair_path.unlink()
            except OSError: pass
            raise ValueError("pairing invitation expired")
        attempts = int(state.get("attempts") or 0)
        if attempts >= PAIR_MAX_ATTEMPTS:
            try: self.pair_path.unlink()
            except OSError: pass
            raise ValueError("pairing invitation locked after too many attempts")
        supplied = hashlib.sha256(normalize_pair_code(code).encode("ascii")).hexdigest()
        if not secrets.compare_digest(str(state.get("code_hash") or ""), supplied):
            state["attempts"] = attempts + 1
            _atomic_json(self.pair_path, state)
            raise ValueError("pairing code is invalid")
        if len(str(auth_token or "")) < 32:
            raise ValueError("pairing authorization token is invalid")
        record = self.trust(peer, source="pairing", auth_token=auth_token, endpoint=peer_endpoint)
        try: self.pair_path.unlink()
        except OSError: pass
        return record

    def pairing_status(self) -> dict:
        state = _load_json(self.pair_path, {})
        if not state or float(state.get("expires") or 0) < _now():
            return {"open": False}
        return {"open": True, "endpoint": state.get("endpoint"), "expires": state.get("expires"),
                "attempts": int(state.get("attempts") or 0)}


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


def join_pairing(local: FabricIdentity, target: str, code: str | None = None, *, name: str = "", hostname: str = "",
                 local_endpoint: str | None = None, timeout: float = 6.0) -> dict:
    endpoint, pair_code = parse_pair_target(target, code)
    me = local.ensure()
    if name or hostname:
        me = local.public(name=name, hostname=hostname)
    transports=local.local_transports()
    if transports: me["transports"]=transports
    token = _new_auth_token()
    body = json.dumps({"schema": PAIR_SCHEMA, "code": pair_code, "identity": me,
                       "auth_token": token, "endpoint": str(local_endpoint or "")}, separators=(",", ":")).encode()
    req = urllib.request.Request(endpoint + "/v1/identity/pair", data=body,
                                 headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            result = json.loads(response.read() or b"{}")
    except Exception as exc:
        raise RuntimeError(f"pairing failed: {exc}") from exc
    remote = result.get("identity") if isinstance(result, dict) else None
    if not isinstance(remote, dict):
        raise RuntimeError(str((result or {}).get("error") or "pairing response had no identity"))
    stored = local.trust(remote, source="pairing", auth_token=token, endpoint=endpoint)
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
        print(json.dumps(store.trusted(public=True), indent=2))
