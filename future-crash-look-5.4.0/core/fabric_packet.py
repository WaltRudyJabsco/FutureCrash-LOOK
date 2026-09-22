#!/usr/bin/env python3
"""Fabric Work Packet v1.

The packet is an immutable work contract. Runtime ownership, leases, attempts and
progress live beside it rather than being written back into it.
"""
from __future__ import annotations

import base64
from contextlib import closing
import hashlib
import json
import mimetypes
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
EVENT_RETENTION_ROWS = 20000
EVENT_RETENTION_SECONDS = 7 * 24 * 60 * 60


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
            with closing(self._connect()) as db:
                db.execute("SELECT 1").fetchone()
            return {"ok": True, "path": str(self.path)}
        except Exception as exc:
            return {"ok": False, "path": str(self.path), "error": str(exc)}

    def _init(self):
        with closing(self._connect()) as db:
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
            CREATE TABLE IF NOT EXISTS decisions (
              id TEXT PRIMARY KEY,
              created REAL NOT NULL,
              expires REAL NOT NULL,
              status TEXT NOT NULL,
              request_json TEXT NOT NULL,
              selected TEXT,
              source TEXT,
              resolved REAL
            );
            CREATE INDEX IF NOT EXISTS decisions_status_expires
              ON decisions(status, expires);
            """)

    def submit(self, packet: dict[str, Any], *, node: str) -> tuple[dict[str, Any], bool]:
        validate_packet(packet)
        pid = packet["id"]
        idem = _dict(packet.get("execution")).get("idempotency")
        blob = canonical_bytes(packet).decode("utf-8")
        digest = packet_digest(packet)
        with self.lock, closing(self._connect()) as db:
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
        with closing(self._connect()) as db:
            row = db.execute("SELECT packet_json FROM packets WHERE id=?", (pid,)).fetchone()
        return json.loads(row["packet_json"]) if row else None

    def get_job(self, pid: str) -> dict[str, Any] | None:
        with closing(self._connect()) as db:
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
        with closing(self._connect()) as db:
            ids = [r["id"] for r in db.execute("SELECT id FROM jobs ORDER BY accepted DESC LIMIT ?", (limit,))]
        return [j for pid in ids if (j := self.get_job(pid))]

    def start(self, pid: str, worker: str) -> int:
        with self.lock, closing(self._connect()) as db:
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
        with self.lock, closing(self._connect()) as db:
            db.execute("UPDATE jobs SET status=?,finished=?,result_packet=?,error=? WHERE id=?",
                       (status, utc_ts(), blob, error, pid))
            db.commit()
        self.event(pid, "result", status, error or status, node=node,
                   data={"result_id": (result or {}).get("id")})

    def request_cancel(self, pid: str, *, node: str, reason: str = "user") -> bool:
        with self.lock, closing(self._connect()) as db:
            row = db.execute("SELECT status FROM jobs WHERE id=?", (pid,)).fetchone()
            if not row: return False
            if row["status"] in {"ok", "failed", "cancelled", "denied"}: return True
            db.execute("UPDATE jobs SET cancel_requested=1 WHERE id=?", (pid,))
            db.commit()
        self.event(pid, "control", "cancel-requested", reason, node=node)
        return True

    def cancelled(self, pid: str) -> bool:
        with closing(self._connect()) as db:
            row = db.execute("SELECT cancel_requested FROM jobs WHERE id=?", (pid,)).fetchone()
        return bool(row and row["cancel_requested"])

    def event(self, pid: str | None, typ: str, phase: str | None, detail: str | None, *, node: str, data: dict[str, Any] | None = None):
        with self.lock, closing(self._connect()) as db:
            cur=db.execute("INSERT INTO events(ts,job_id,type,phase,detail,node,data_json) VALUES(?,?,?,?,?,?,?)",
                       (utc_ts(), pid, typ, phase, detail, node,
                        json.dumps(data or {}, separators=(",",":"), ensure_ascii=False)))
            # The event ledger is an operational tail, not an infinite message queue.
            # Prune occasionally so disconnected dashboards cannot create permanent debt.
            seq=int(cur.lastrowid or 0)
            if seq and seq % 256 == 0:
                db.execute("DELETE FROM events WHERE ts < ?", (utc_ts()-EVENT_RETENTION_SECONDS,))
                db.execute("DELETE FROM events WHERE seq <= ?", (max(0,seq-EVENT_RETENTION_ROWS),))
            db.commit()

    def events(self, *, since: int = 0, limit: int = 128) -> list[dict[str, Any]]:
        limit = max(1, min(int(limit), 512))
        with closing(self._connect()) as db:
            rows = db.execute("SELECT * FROM events WHERE seq>? ORDER BY seq ASC LIMIT ?", (int(since), limit)).fetchall()
        out=[]
        for row in rows:
            d=dict(row)
            try: d["data"] = json.loads(d.pop("data_json") or "{}")
            except Exception: d["data"] = {}
            out.append(d)
        return out

    def recent_events(self, *, limit: int = 128) -> list[dict[str, Any]]:
        """Return the newest event tail in chronological order.

        Dashboards want current truth, not the first 128 events ever recorded.
        Cursor consumers should continue to use events(since=...).
        """
        limit = max(1, min(int(limit), 512))
        with closing(self._connect()) as db:
            rows = db.execute("SELECT * FROM events ORDER BY seq DESC LIMIT ?", (limit,)).fetchall()
        out=[]
        for row in reversed(rows):
            d=dict(row)
            try: d["data"] = json.loads(d.pop("data_json") or "{}")
            except Exception: d["data"] = {}
            out.append(d)
        return out

    def add_decision(self, request: dict[str, Any], *, node: str) -> dict[str, Any]:
        """Persist a portable DecisionRequest without tying it to any renderer."""
        if not isinstance(request, dict) or request.get("schema") != "fabric-decision-v1":
            raise ValueError("fabric-decision-v1 request required")
        did=str(request.get("id") or "")
        if not did:
            raise ValueError("decision id required")
        blob=json.dumps(request,separators=(",",":"),ensure_ascii=False)
        with self.lock, closing(self._connect()) as db:
            db.execute(
                "INSERT OR IGNORE INTO decisions(id,created,expires,status,request_json) VALUES(?,?,?,?,?)",
                (did,float(request.get("created") or utc_ts()),float(request.get("expires") or utc_ts()),"pending",blob),
            )
            db.commit()
        self.event(request.get("job_id"),"decision","pending",request.get("question"),node=node,
                   data={"decision_id":did,"expires":request.get("expires"),"preferred":request.get("preferred")})
        return self.get_decision(did) or request

    @staticmethod
    def _decision_row(row) -> dict[str, Any] | None:
        if not row:
            return None
        try: request=json.loads(row["request_json"] or "{}")
        except Exception: request={}
        request["status"]=row["status"]
        request["selected"]=row["selected"]
        request["response_source"]=row["source"]
        request["resolved"]=row["resolved"]
        return request

    def get_decision(self, did: str) -> dict[str, Any] | None:
        with closing(self._connect()) as db:
            row=db.execute("SELECT * FROM decisions WHERE id=?",(str(did),)).fetchone()
        return self._decision_row(row)

    def decisions(self, *, pending_only: bool = False, limit: int = 64) -> list[dict[str, Any]]:
        limit=max(1,min(int(limit),256))
        query="SELECT * FROM decisions"
        args=[]
        if pending_only:
            query += " WHERE status='pending'"
        query += " ORDER BY created DESC LIMIT ?"
        args.append(limit)
        with closing(self._connect()) as db:
            rows=db.execute(query,tuple(args)).fetchall()
        return [d for row in rows if (d:=self._decision_row(row))]

    def resolve_decision(self, did: str, selected: str, *, source: str, node: str) -> dict[str, Any]:
        """Resolve exactly once. Late answers are returned as conflicts, not rewrites."""
        did=str(did); selected=str(selected)
        with self.lock, closing(self._connect()) as db:
            row=db.execute("SELECT * FROM decisions WHERE id=?",(did,)).fetchone()
            if not row:
                raise KeyError(did)
            current=self._decision_row(row) or {}
            if current.get("status") != "pending":
                return current
            allowed={str(x.get("value")) for x in (current.get("choices") or []) if isinstance(x,dict)}
            if selected not in allowed:
                raise ValueError(f"invalid decision choice: {selected}")
            when=utc_ts()
            db.execute("UPDATE decisions SET status='answered',selected=?,source=?,resolved=? WHERE id=? AND status='pending'",
                       (selected,str(source or "human"),when,did))
            db.commit()
        result=self.get_decision(did) or {}
        self.event(result.get("job_id"),"decision","answered",selected,node=node,
                   data={"decision_id":did,"source":source})
        return result

    def expire_decisions(self, *, node: str) -> list[dict[str, Any]]:
        """Resolve due optional decisions to their declared fallback without blocking work."""
        now=utc_ts(); expired=[]
        with self.lock, closing(self._connect()) as db:
            rows=db.execute("SELECT * FROM decisions WHERE status='pending' AND expires<=? ORDER BY expires ASC",(now,)).fetchall()
            for row in rows:
                current=self._decision_row(row) or {}
                fallback=str(current.get("fallback") or "defer")
                choices={str(x.get("value")) for x in (current.get("choices") or []) if isinstance(x,dict)}
                selected=fallback if fallback in choices else None
                status="timed_out"
                db.execute("UPDATE decisions SET status=?,selected=?,source='timeout',resolved=? WHERE id=? AND status='pending'",
                           (status,selected,now,row["id"]))
                current.update(status=status,selected=selected,response_source="timeout",resolved=now,timeout_action=fallback)
                expired.append(current)
            db.commit()
        for current in expired:
            self.event(current.get("job_id"),"decision","timeout",str(current.get("timeout_action") or "defer"),node=node,
                       data={"decision_id":current.get("id"),"selected":current.get("selected")})
        return expired


class ArtifactStore:
    """Content-addressed artifacts with small managed blobs and large file references.

    Small generated/context artifacts remain copied into the store. Large existing files
    can instead be registered in place: the digest identifies their observed contents,
    while the source path remains a replaceable physical location.
    """
    HASH_CHUNK_BYTES = 1024 * 1024

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
            meta.write_text(json.dumps({
                "digest": digest, "bytes": len(data), "media_type": media_type,
                "name": name, "created": utc_ts(), "storage": "managed",
            }, indent=2) + "\n")
            os.chmod(meta, 0o600)
        return self.metadata(digest)

    def put_base64(self, encoded: str, **kwargs) -> dict[str, Any]:
        return self.put(base64.b64decode(encoded.encode("ascii"), validate=True), **kwargs)

    def register_file(self, path: str | Path, *, media_type: str | None = None, name: str | None = None) -> dict[str, Any]:
        """Register an existing local file without copying it into Fabric storage.

        Hashing happens once at registration. Later reads verify the observed size and
        nanosecond mtime before serving so a mutable path cannot silently impersonate
        the content-addressed artifact. Re-register after moving or changing a file.
        """
        source = Path(path).expanduser().resolve()
        if not source.is_file():
            raise FileNotFoundError(source)
        stat = source.stat()
        digest_hash = hashlib.sha256()
        with source.open("rb") as fh:
            while True:
                chunk = fh.read(self.HASH_CHUNK_BYTES)
                if not chunk:
                    break
                digest_hash.update(chunk)
        hexdigest = digest_hash.hexdigest()
        digest = f"sha256:{hexdigest}"
        guessed = mimetypes.guess_type(source.name)[0] or "application/octet-stream"
        meta = self.root / f"{hexdigest}.json"
        managed_blob = self.root / hexdigest
        if managed_blob.is_file() and meta.is_file():
            # A durable managed copy is already the strongest local location. Do not
            # replace it with a path reference that could later disappear.
            return self.metadata(digest)
        record = {
            "digest": digest,
            "bytes": int(stat.st_size),
            "media_type": str(media_type or guessed),
            "name": str(name or source.name),
            "created": utc_ts(),
            "storage": "external",
            "path": str(source),
            "mtime_ns": int(stat.st_mtime_ns),
        }
        tmp = meta.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(record, indent=2) + "\n")
        os.chmod(tmp, 0o600)
        tmp.replace(meta)
        return record

    def _hex(self, digest: str) -> str:
        if not digest.startswith("sha256:") or len(digest) != 71:
            raise ValueError("invalid sha256 artifact digest")
        return digest.split(":", 1)[1]

    def metadata(self, digest: str) -> dict[str, Any]:
        h = self._hex(digest)
        meta = self.root / f"{h}.json"
        if not meta.exists():
            raise FileNotFoundError(digest)
        data = json.loads(meta.read_text())
        data.setdefault("storage", "managed")  # Backward compatibility with pre-5.2.15 artifacts.
        return data

    def list_metadata(self) -> list[dict[str, Any]]:
        """List known local artifacts without touching or loading their payload bytes."""
        rows: list[dict[str, Any]] = []
        for meta in sorted(self.root.glob("*.json"), key=lambda p: p.name):
            try:
                data = json.loads(meta.read_text())
            except (OSError, ValueError, TypeError):
                continue
            if not isinstance(data, dict) or not str(data.get("digest") or "").startswith("sha256:"):
                continue
            data.setdefault("storage", "managed")
            rows.append(data)
        return rows

    def path_for(self, digest: str) -> tuple[dict[str, Any], Path]:
        """Resolve an artifact to a local readable path without loading its bytes."""
        h = self._hex(digest)
        meta = self.metadata(digest)
        if meta.get("storage") == "external":
            path = Path(str(meta.get("path") or ""))
            if not path.is_file():
                raise FileNotFoundError(digest)
            stat = path.stat()
            if int(stat.st_size) != int(meta.get("bytes") or -1) or int(stat.st_mtime_ns) != int(meta.get("mtime_ns") or -1):
                raise IOError(f"artifact source changed since registration: {digest}")
            return meta, path
        path = self.root / h
        if not path.is_file():
            raise FileNotFoundError(digest)
        return meta, path

    def get(self, digest: str) -> tuple[dict[str, Any], bytes]:
        """Load a small artifact into memory; large artifacts must use streaming/range I/O."""
        h = self._hex(digest)
        meta, path = self.path_for(digest)
        if int(meta.get("bytes") or 0) > MAX_INLINE_ARTIFACT_BYTES:
            raise ValueError("artifact is too large for in-memory retrieval; use stream/range access")
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != h:
            raise IOError(f"artifact integrity check failed: {digest}")
        return meta, data
