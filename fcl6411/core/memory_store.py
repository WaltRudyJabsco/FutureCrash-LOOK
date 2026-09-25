#!/usr/bin/env python3
"""Tiny replicated Fabric memory store.

Shared/persona scopes are safe to replicate across the user's trusted Fabric.
Node scope is intentionally local. The store is boring JSON so it remains
inspectable and recoverable without the daemon.
"""
from __future__ import annotations

import hashlib
import json
import os
import socket
import time
from pathlib import Path

VERSION = 1
MAX_ITEMS = 256
MAX_TEXT = 1200


def default_path() -> Path:
    return Path.home() / ".local" / "share" / "look" / "fabric_memory.json"


def node_name() -> str:
    return os.environ.get("FCL_NODE_NAME", "").strip() or socket.gethostname().split(".")[0]


def _empty() -> dict:
    return {"version": VERSION, "items": []}


def _clean_text(text: str) -> str:
    return " ".join(str(text or "").split())[:MAX_TEXT].strip()


def _valid_scope(scope: str) -> bool:
    return scope == "shared" or scope.startswith("persona:") or scope.startswith("node:")


def _item_id(scope: str, text: str) -> str:
    raw = (scope + "\0" + text.casefold()).encode("utf-8", "replace")
    return hashlib.sha256(raw).hexdigest()[:20]


class FabricMemory:
    def __init__(self, path: Path | str | None = None):
        self.path = Path(path or default_path())

    def load(self) -> dict:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                return _empty()
            items = data.get("items") if isinstance(data.get("items"), list) else []
            clean = []
            for row in items:
                if not isinstance(row, dict):
                    continue
                scope = str(row.get("scope") or "")
                text = _clean_text(row.get("text") or "")
                if not text or not _valid_scope(scope):
                    continue
                clean.append({
                    "id": str(row.get("id") or _item_id(scope, text)),
                    "scope": scope,
                    "text": text,
                    "importance": max(1, min(100, int(row.get("importance") or 60))),
                    "created_at": float(row.get("created_at") or time.time()),
                    "updated_at": float(row.get("updated_at") or row.get("created_at") or time.time()),
                    "source_node": str(row.get("source_node") or "unknown")[:128],
                })
            clean.sort(key=lambda x: (x["updated_at"], x["importance"]))
            return {"version": VERSION, "items": clean[-MAX_ITEMS:]}
        except Exception:
            return _empty()

    def save(self, data: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        try:
            os.chmod(tmp, 0o600)
        except OSError:
            pass
        tmp.replace(self.path)
        try:
            os.chmod(self.path, 0o600)
        except OSError:
            pass

    def add(self, scope: str, text: str, importance: int = 60, source_node: str | None = None) -> dict:
        scope = str(scope or "").strip().lower()
        text = _clean_text(text)
        if not _valid_scope(scope):
            raise ValueError("scope must be shared, persona:<name>, or node:<name>")
        if not text:
            raise ValueError("memory text required")
        now = time.time()
        data = self.load()
        iid = _item_id(scope, text)
        found = None
        for item in data["items"]:
            if item.get("id") == iid:
                found = item
                break
        if found:
            found["importance"] = max(int(found.get("importance") or 0), max(1, min(100, int(importance))))
            found["updated_at"] = now
            found["source_node"] = str(source_node or found.get("source_node") or node_name())[:128]
            item = found
        else:
            item = {
                "id": iid,
                "scope": scope,
                "text": text,
                "importance": max(1, min(100, int(importance))),
                "created_at": now,
                "updated_at": now,
                "source_node": str(source_node or node_name())[:128],
            }
            data["items"].append(item)
        data["items"] = sorted(data["items"], key=lambda x: (x["updated_at"], x["importance"]))[-MAX_ITEMS:]
        self.save(data)
        return dict(item)

    def merge(self, incoming: list[dict]) -> dict:
        data = self.load()
        by_id = {str(x.get("id")): x for x in data["items"] if x.get("id")}
        added = updated = 0
        for row in incoming or []:
            if not isinstance(row, dict):
                continue
            scope = str(row.get("scope") or "").strip().lower()
            text = _clean_text(row.get("text") or "")
            # Node memories never leave their owner; ignore remote node scope.
            if not text or not (scope == "shared" or scope.startswith("persona:")):
                continue
            iid = str(row.get("id") or _item_id(scope, text))
            candidate = {
                "id": iid,
                "scope": scope,
                "text": text,
                "importance": max(1, min(100, int(row.get("importance") or 60))),
                "created_at": float(row.get("created_at") or time.time()),
                "updated_at": float(row.get("updated_at") or row.get("created_at") or time.time()),
                "source_node": str(row.get("source_node") or "peer")[:128],
            }
            old = by_id.get(iid)
            if old is None:
                by_id[iid] = candidate
                added += 1
            elif candidate["updated_at"] > float(old.get("updated_at") or 0):
                by_id[iid] = candidate
                updated += 1
        items = sorted(by_id.values(), key=lambda x: (x["updated_at"], x["importance"]))[-MAX_ITEMS:]
        data = {"version": VERSION, "items": items}
        self.save(data)
        return {"ok": True, "added": added, "updated": updated, "count": len(items)}

    def public(self, include_local: bool = True) -> dict:
        items = self.load()["items"]
        if not include_local:
            items = [x for x in items if x.get("scope") == "shared" or str(x.get("scope") or "").startswith("persona:")]
        return {"version": VERSION, "node": node_name(), "items": items}

    def relevant(self, persona: str | None = None, query: str = "", limit: int = 8, include_local: bool = True) -> list[dict]:
        q = {t for t in "".join(c.lower() if c.isalnum() else " " for c in str(query or "")).split() if len(t) > 2}
        allowed = {"shared"}
        if persona:
            allowed.add("persona:" + str(persona).strip().lower())
        if include_local:
            allowed.add("node:" + node_name().lower())
        ranked = []
        now = time.time()
        for item in self.load()["items"]:
            if str(item.get("scope") or "").lower() not in allowed:
                continue
            words = {t for t in "".join(c.lower() if c.isalnum() else " " for c in item.get("text", "")).split() if len(t) > 2}
            overlap = len(q & words) if q else 0
            importance = int(item.get("importance") or 0)
            age_days = max(0.0, (now - float(item.get("updated_at") or now)) / 86400.0)
            score = overlap * 20 + importance - min(30, age_days)
            ranked.append((score, item))
        ranked.sort(key=lambda x: x[0], reverse=True)
        return [dict(x[1]) for x in ranked[:max(1, int(limit))]]


def context_text(persona: str | None = None, query: str = "", limit: int = 8) -> str:
    rows = FabricMemory().relevant(persona=persona, query=query, limit=limit)
    if not rows:
        return ""
    lines = ["Fabric memory (user-owned context; use only when relevant):"]
    for row in rows:
        lines.append(f"- [{row['scope']}] {row['text']}")
    return "\n".join(lines)
