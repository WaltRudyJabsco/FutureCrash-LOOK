#!/usr/bin/env python3
"""Fabric Work Packet v1.

The packet is an immutable work contract. Runtime ownership, leases, attempts and
progress live beside it rather than being written back into it.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import sqlite3
import threading
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PROTOCOL = "fwp/1"
PACKET_KINDS = {"task", "event", "observation", "result", "artifact", "control"}
PRIORITIES = {"interactive", "followup", "background"}
MAX_PACKET_BYTES = 512 * 1024
MAX_INLINE_ARTIFACT_BYTES = 8 * 1024 * 1024


def utc_ts() -> float:
    return time.time()


def new_id(prefix: str = "fwp") -> str:
    # Time is deliberately outside the identity hash: IDs need to be cheap and unique,
    # while immutable artifact integrity uses SHA-256 separately.
    return f"{prefix}_{uuid.uuid4().hex}"


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def packet_digest(packet: dict[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(canonical_bytes(packet)).hexdigest()


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def normalize_packet(raw: dict[str, Any], *, origin: str) -> dict[str, Any]:
    """Create the immutable canonical packet once, at the dispatch edge."""
    if not isinstance(raw, dict):
        raise ValueError("packet must be an object")
    packet = dict(raw)
    packet.setdefault("fabric", PROTOCOL)
    if packet["fabric"] != PROTOCOL:
        raise ValueError(f"unsupported Fabric packet protocol: {packet['fabric']}")
    packet.setdefault("id", new_id())
    packet.setdefault("kind", "task")
    packet.setdefault("created", utc_ts())
    packet.setdefault("origin", origin)
    packet.setdefault("relationships", {})
    packet.setdefault("work", {})
    packet.setdefault("capabilities", {})
    packet.setdefault("context", {})
    packet.setdefault("execution", {})
    packet.setdefault("authority", {})
    packet.setdefault("delivery", {})
    packet.setdefault("provenance", {})
    packet.setdefault("extensions", {})

    execution = dict(_dict(packet["execution"]))
    execution.setdefault("priority", "interactive")
    execution.setdefault("cancellable", True)
    execution.setdefault("idempotency", packet["id"])
    execution.setdefault("budget", {})
    packet["execution"] = execution

    authority = dict(_dict(packet["authority"]))
    authority.setdefault("principal", "user")
    authority.setdefault("grants", ["observe", "model.infer"])
    authority.setdefault("confirmed_operations", [])
    packet["authority"] = authority

    validate_packet(packet)
    return packet


def validate_packet(packet: dict[str, Any]) -> None:
    if packet.get("fabric") != PROTOCOL:
        raise ValueError("fabric must be fwp/1")
    if packet.get("kind") not in PACKET_KINDS:
        raise ValueError("unsupported packet kind")
    if not isinstance(packet.get("id"), str) or not packet["id"]:
        raise ValueError("packet id required")
    if not isinstance(packet.get("origin"), str) or not packet["origin"]:
        raise ValueError("packet origin required")
    if packet.get("kind") == "task":
        operation = _dict(packet.get("work")).get("operation")
        if not isinstance(operation, str) or not operation:
            raise ValueError("task work.operation required")
    priority = _dict(packet.get("execution")).get("priority", "interactive")
    if priority not in PRIORITIES:
        raise ValueError(f"invalid priority: {priority}")
    raw = canonical_bytes(packet)
    if len(raw) > MAX_PACKET_BYTES:
        raise ValueError(f"packet exceeds {MAX_PACKET_BYTES} bytes; use context/artifact references")


def packet_summary(packet: dict[str, Any]) -> dict[str, Any]:
    work = _dict(packet.get("work"))
    delivery = _dict(packet.get("delivery"))
    execution = _dict(packet.get("execution"))
    return {
        "id": packet.get("id"),
        "kind": packet.get("kind"),
        "operation": work.get("operation"),
        "objective": work.get("objective"),
        "origin": packet.get("origin"),
        "target": delivery.get("target"),
        "priority": execution.get("priority"),
        "digest": packet_digest(packet),
    }


class FabricStore:
    """Durable packet ledger: immutable packets + mutable execution records/events."""
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self._init()

    def _connect(self):
        # Mutable ledger state must recover if its parent disappears transiently
        # during an update. Retry SQLITE_CANTOPEN once after recreating the parent.
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            db = sqlite3.connect(self.path, timeout=5.0)
        except sqlite3.OperationalError:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            db = sqlite3.connect(self.path, timeout=5.0)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA busy_timeout=5000")
        return db

    def health(self):
        try:
            with self._connect() as db:
                db.execute("SELECT 1").fetchone()
            return {"ok": True, "path": str(self.path)}
        except Exception as exc:
            return {"ok": False, "path": str(self.path), "error": str(exc)}

    def _init(self):
        with self._connect() as db:
            db.executescript("""
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS packets (
              id TEXT PRIMARY KEY,
              digest TEXT NOT NULL,
              packet_json TEXT NOT NULL,
              created REAL NOT NULL,
              idempotency TEXT
            );
            CREATE UNIQUE INDEX IF NOT EXISTS packets_idempotency
              ON packets(idempotency) WHERE idempotency IS NOT NULL;
            CREATE TABLE IF NOT EXISTS jobs (
              id TEXT PRIMARY KEY,
              status TEXT NOT NULL,
              attempt INTEGER NOT NULL DEFAULT 0,
              worker TEXT,
              accepted REAL NOT NULL,
              started REAL,
              finished REAL,
              result_packet TEXT,
              error TEXT,
              cancel_requested INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS events (
              seq INTEGER PRIMARY KEY AUTOINCREMENT,
              ts REAL NOT NULL,
              job_id TEXT,
              type TEXT NOT NULL,
              phase TEXT,
              detail TEXT,
              node TEXT,
              data_json TEXT
            );
            """)

    def submit(self, packet: dict[str, Any], *, node: str) -> tuple[dict[str, Any], bool]:
        validate_packet(packet)
        pid = packet["id"]
        idem = _dict(packet.get("execution")).get("idempotency")
        blob = canonical_bytes(packet).decode("utf-8")
        digest = packet_digest(packet)
        with self.lock, self._connect() as db:
            existing = db.execute("SELECT digest FROM packets WHERE id=?", (pid,)).fetchone()
            if existing:
                if existing["digest"] != digest:
                    raise ValueError(f"packet id collision with different immutable content: {pid}")
                return self.get_job(pid), False
            if idem:
                row = db.execute("SELECT id FROM packets WHERE idempotency=?", (str(idem),)).fetchone()
                if row:
                    return self.get_job(row["id"]), False
            db.execute("INSERT INTO packets(id,digest,packet_json,created,idempotency) VALUES(?,?,?,?,?)",
                       (pid, digest, blob, float(packet["created"]), str(idem) if idem else None))
            db.execute("INSERT INTO jobs(id,status,accepted) VALUES(?,?,?)", (pid, "queued", utc_ts()))
            db.commit()
        self.event(pid, "accepted", "queued", "packet accepted", node=node,
                   data={"digest": digest})
        return self.get_job(pid), True

    def get_packet(self, pid: str) -> dict[str, Any] | None:
        with self._connect() as db:
            row = db.execute("SELECT packet_json FROM packets WHERE id=?", (pid,)).fetchone()
        return json.loads(row["packet_json"]) if row else None

    def get_job(self, pid: str) -> dict[str, Any] | None:
        with self._connect() as db:
            row = db.execute("SELECT * FROM jobs WHERE id=?", (pid,)).fetchone()
        if not row:
            return None
        d = dict(row)
        d["cancel_requested"] = bool(d["cancel_requested"])
        if d.get("result_packet"):
            try: d["result"] = json.loads(d["result_packet"])
            except Exception: d["result"] = None
        d.pop("result_packet", None)
        packet = self.get_packet(pid)
        if packet:
            d["packet"] = packet_summary(packet)
        return d

    def jobs(self, limit: int = 32) -> list[dict[str, Any]]:
        limit = max(1, min(int(limit), 256))
        with self._connect() as db:
            ids = [r["id"] for r in db.execute("SELECT id FROM jobs ORDER BY accepted DESC LIMIT ?", (limit,))]
        return [j for pid in ids if (j := self.get_job(pid))]

    def start(self, pid: str, worker: str) -> int:
        with self.lock, self._connect() as db:
            row = db.execute("SELECT attempt,status FROM jobs WHERE id=?", (pid,)).fetchone()
            if not row: raise KeyError(pid)
            attempt = int(row["attempt"]) + 1
            db.execute("UPDATE jobs SET status='running',attempt=?,worker=?,started=?,finished=NULL,error=NULL WHERE id=?",
                       (attempt, worker, utc_ts(), pid))
            db.commit()
        self.event(pid, "attempt", "running", f"attempt {attempt} started", node=worker,
                   data={"attempt": attempt})
        return attempt

    def finish(self, pid: str, status: str, *, result: dict[str, Any] | None = None, error: str | None = None, node: str = ""):
        blob = json.dumps(result, separators=(",", ":"), ensure_ascii=False) if result is not None else None
        with self.lock, self._connect() as db:
            db.execute("UPDATE jobs SET status=?,finished=?,result_packet=?,error=? WHERE id=?",
                       (status, utc_ts(), blob, error, pid))
            db.commit()
        self.event(pid, "result", status, error or status, node=node,
                   data={"result_id": (result or {}).get("id")})

    def request_cancel(self, pid: str, *, node: str, reason: str = "user") -> bool:
        with self.lock, self._connect() as db:
            row = db.execute("SELECT status FROM jobs WHERE id=?", (pid,)).fetchone()
            if not row: return False
            if row["status"] in {"ok", "failed", "cancelled", "denied"}: return True
            db.execute("UPDATE jobs SET cancel_requested=1 WHERE id=?", (pid,))
            db.commit()
        self.event(pid, "control", "cancel-requested", reason, node=node)
        return True

    def cancelled(self, pid: str) -> bool:
        with self._connect() as db:
            row = db.execute("SELECT cancel_requested FROM jobs WHERE id=?", (pid,)).fetchone()
        return bool(row and row["cancel_requested"])

    def event(self, pid: str | None, typ: str, phase: str | None, detail: str | None, *, node: str, data: dict[str, Any] | None = None):
        with self.lock, self._connect() as db:
            db.execute("INSERT INTO events(ts,job_id,type,phase,detail,node,data_json) VALUES(?,?,?,?,?,?,?)",
                       (utc_ts(), pid, typ, phase, detail, node,
                        json.dumps(data or {}, separators=(",", ":"), ensure_ascii=False)))
            db.commit()

    def events(self, *, since: int = 0, limit: int = 128) -> list[dict[str, Any]]:
        limit = max(1, min(int(limit), 512))
        with self._connect() as db:
            rows = db.execute("SELECT * FROM events WHERE seq>? ORDER BY seq ASC LIMIT ?", (int(since), limit)).fetchall()
        out=[]
        for row in rows:
            d=dict(row)
            try: d["data"] = json.loads(d.pop("data_json") or "{}")
            except Exception: d["data"] = {}
            out.append(d)
        return out


class ArtifactStore:
    """Small content-addressed object store for packet context and durable results."""
    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def put(self, data: bytes, *, media_type: str = "application/octet-stream", name: str | None = None) -> dict[str, Any]:
        if len(data) > MAX_INLINE_ARTIFACT_BYTES:
            raise ValueError(f"artifact exceeds inline limit of {MAX_INLINE_ARTIFACT_BYTES} bytes")
        hexdigest = hashlib.sha256(data).hexdigest()
        digest = f"sha256:{hexdigest}"
        blob = self.root / hexdigest
        meta = self.root / f"{hexdigest}.json"
        if not blob.exists():
            tmp = blob.with_suffix(".tmp")
            tmp.write_bytes(data)
            os.chmod(tmp, 0o600)
            tmp.replace(blob)
            meta.write_text(json.dumps({"digest": digest, "bytes": len(data), "media_type": media_type,
                                        "name": name, "created": utc_ts()}, indent=2) + "\n")
            os.chmod(meta, 0o600)
        return self.metadata(digest)

    def put_base64(self, encoded: str, **kwargs) -> dict[str, Any]:
        return self.put(base64.b64decode(encoded.encode("ascii"), validate=True), **kwargs)

    def _hex(self, digest: str) -> str:
        if not digest.startswith("sha256:") or len(digest) != 71:
            raise ValueError("invalid sha256 artifact digest")
        return digest.split(":", 1)[1]

    def metadata(self, digest: str) -> dict[str, Any]:
        h = self._hex(digest)
        meta = self.root / f"{h}.json"
        if not meta.exists(): raise FileNotFoundError(digest)
        return json.loads(meta.read_text())

    def get(self, digest: str) -> tuple[dict[str, Any], bytes]:
        h = self._hex(digest)
        meta = self.metadata(digest)
        data = (self.root / h).read_bytes()
        if hashlib.sha256(data).hexdigest() != h:
            raise IOError(f"artifact integrity check failed: {digest}")
        return meta, data
