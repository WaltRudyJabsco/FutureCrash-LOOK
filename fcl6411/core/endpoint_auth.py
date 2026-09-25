#!/usr/bin/env python3
"""Accountless browser/endpoint authorization for Fabric web surfaces.

A browser first gets a short pending code. A trusted local operator approves that
code for one session or as a trusted device. QR invitations are one-use shortcuts
that still issue a scoped endpoint credential; no account or password is involved.
"""
from __future__ import annotations

import hashlib
import json
import os
import secrets
import tempfile
import time
from pathlib import Path

SCHEMA = "fabric-endpoints-v1"
PENDING_TTL_SECONDS = 300
ONCE_TTL_SECONDS = 12 * 60 * 60
INVITE_TTL_SECONDS = 300
DEFAULT_SCOPES = ["signal.view", "lo.use", "media.output", "camera.offer", "decisions.answer"]


def _now() -> float:
    return time.time()


def _hash(token: str) -> str:
    return hashlib.sha256(str(token or "").encode("utf-8")).hexdigest()


def _atomic_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.name + ".", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, sort_keys=True)
            fh.write("\n")
        os.chmod(tmp, 0o600)
        os.replace(tmp, path)
    finally:
        try: os.unlink(tmp)
        except FileNotFoundError: pass


def _load(path: Path) -> dict:
    try:
        d = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(d, dict):
            return d
    except Exception:
        pass
    return {"schema": SCHEMA, "pending": {}, "trusted": {}, "sessions": {}, "invites": {}}


def _code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def _token() -> str:
    return secrets.token_urlsafe(32)


class EndpointAuth:
    def __init__(self, path: Path | None = None):
        self.path = Path(path or (Path.home() / ".config/future-crash-look/endpoints.json"))

    def _read(self) -> dict:
        data = _load(self.path)
        for key in ("pending", "trusted", "sessions", "invites"):
            if not isinstance(data.get(key), dict): data[key] = {}
        data["schema"] = SCHEMA
        return data

    def _prune(self, data: dict) -> None:
        t = _now()
        for key in ("pending", "sessions", "invites"):
            for ident, row in list(data[key].items()):
                if float((row or {}).get("expires") or 0) <= t:
                    data[key].pop(ident, None)

    def request(self, *, user_agent: str = "", remote: str = "") -> dict:
        data = self._read(); self._prune(data)
        pending_id = _token()
        code = _code()
        while any(str(x.get("code")) == code for x in data["pending"].values()):
            code = _code()
        row = {"id": pending_id, "code": code, "created": _now(), "expires": _now()+PENDING_TTL_SECONDS,
               "user_agent": str(user_agent)[:240], "remote": str(remote)[:120], "approved": ""}
        data["pending"][_hash(pending_id)] = row
        _atomic_json(self.path, data)
        return dict(row)

    def pending_status(self, pending_id: str) -> dict | None:
        data = self._read(); self._prune(data)
        row = data["pending"].get(_hash(pending_id))
        return dict(row) if isinstance(row, dict) else None

    def allow(self, code: str, mode: str = "once") -> dict:
        mode = str(mode or "once").casefold()
        if mode not in {"once", "trust"}: raise ValueError("mode must be once or trust")
        data = self._read(); self._prune(data)
        row = next((r for r in data["pending"].values() if str(r.get("code")) == str(code).strip()), None)
        if not row: raise ValueError("endpoint code not found or expired")
        row["approved"] = mode
        row["approved_at"] = _now()
        _atomic_json(self.path, data)
        return dict(row)

    def redeem_pending(self, pending_id: str, *, label: str = "Browser") -> dict | None:
        data = self._read(); self._prune(data)
        key = _hash(pending_id)
        row = data["pending"].get(key)
        if not row or row.get("approved") not in {"once", "trust"}:
            _atomic_json(self.path, data); return None
        mode = row["approved"]
        token = _token(); endpoint_id = "ep-" + secrets.token_hex(8)
        record = {"endpoint_id": endpoint_id, "label": str(label or "Browser")[:80], "created": _now(),
                  "last_seen": _now(), "scopes": list(DEFAULT_SCOPES), "mode": mode, "token_hash": _hash(token)}
        if mode == "trust": data["trusted"][endpoint_id] = record
        else:
            record["expires"] = _now() + ONCE_TTL_SECONDS
            data["sessions"][endpoint_id] = record
        data["pending"].pop(key, None)
        _atomic_json(self.path, data)
        return {"token": token, **{k:v for k,v in record.items() if k != "token_hash"}}

    def verify(self, token: str) -> dict | None:
        if not token: return None
        data = self._read(); self._prune(data); digest = _hash(token)
        found = None
        for bucket in ("trusted", "sessions"):
            for endpoint_id, row in data[bucket].items():
                if secrets.compare_digest(str(row.get("token_hash") or ""), digest):
                    found = {k:v for k,v in row.items() if k != "token_hash"}; break
            if found: break
        return found

    def revoke(self, endpoint_id: str) -> bool:
        data = self._read(); removed = False
        for bucket in ("trusted", "sessions"):
            removed = data[bucket].pop(str(endpoint_id), None) is not None or removed
        if removed: _atomic_json(self.path, data)
        return removed

    def list(self) -> dict:
        data = self._read(); self._prune(data); _atomic_json(self.path, data)
        def clean(row): return {k:v for k,v in row.items() if k != "token_hash"}
        return {"schema": SCHEMA,
                "pending": [clean(r) for r in data["pending"].values()],
                "trusted": [clean(r) for r in data["trusted"].values()],
                "sessions": [clean(r) for r in data["sessions"].values()]}

    def create_invite(self, base_url: str, *, mode: str = "trust") -> dict:
        mode = str(mode or "trust").casefold()
        if mode not in {"once", "trust"}: raise ValueError("mode must be once or trust")
        base = str(base_url or "").rstrip("/")
        if not base.startswith(("http://", "https://")): raise ValueError("endpoint URL must be http:// or https://")
        data = self._read(); self._prune(data)
        token = _token(); data["invites"][_hash(token)] = {"created":_now(), "expires":_now()+INVITE_TTL_SECONDS, "mode":mode}
        _atomic_json(self.path, data)
        return {"token": token, "url": base + "/?fcl_invite=" + token, "mode": mode, "expires": _now()+INVITE_TTL_SECONDS}

    def redeem_invite(self, token: str, *, label: str = "Browser") -> dict | None:
        data = self._read(); self._prune(data); key = _hash(token)
        invite = data["invites"].pop(key, None)
        if not invite:
            _atomic_json(self.path, data); return None
        auth_token = _token(); endpoint_id = "ep-" + secrets.token_hex(8); mode = invite.get("mode") or "trust"
        record = {"endpoint_id": endpoint_id, "label": str(label or "Browser")[:80], "created": _now(),
                  "last_seen": _now(), "scopes": list(DEFAULT_SCOPES), "mode": mode, "token_hash": _hash(auth_token)}
        if mode == "trust": data["trusted"][endpoint_id] = record
        else:
            record["expires"] = _now()+ONCE_TTL_SECONDS; data["sessions"][endpoint_id] = record
        _atomic_json(self.path, data)
        return {"token": auth_token, **{k:v for k,v in record.items() if k != "token_hash"}}
