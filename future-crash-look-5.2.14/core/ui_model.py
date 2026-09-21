"""Small shared presentation model for Fabric surfaces.

The core owns meaning; terminal/web/Future Crash renderers own appearance.
This module intentionally has no terminal, HTTP, or HTML dependencies.
"""
from __future__ import annotations

from typing import Any


DASH_ACTIONS = (
    {"id": "quit", "label": "quit", "key": "q"},
    {"id": "mini", "label": "mini", "key": "m"},
    {"id": "beacon", "label": "beacon", "key": "b"},
    {"id": "lights", "label": "lights", "key": "l"},
    {"id": "watch", "label": "watch", "key": "w"},
    {"id": "settings", "label": "settings", "key": "s"},
    {"id": "doctor", "label": "doctor", "key": "d"},
    {"id": "restart", "label": "restart", "key": "r", "dangerous": True},
    {"id": "refresh", "label": "refresh", "key": "space"},
)


def actions(*, mini: bool = False) -> list[dict[str, Any]]:
    """Return renderer-neutral actions for a Fabric dashboard surface."""
    out = [dict(item) for item in DASH_ACTIONS]
    for item in out:
        if item["id"] == "mini":
            item["label"] = "full" if mini else "mini"
        if mini and item["id"] in {"watch", "settings", "doctor", "restart"}:
            item["hidden"] = True
    return out


def _node_rows(data: dict[str, Any]) -> list[dict[str, Any]]:
    snap = data.get("nodes") or {}
    local = snap.get("self") or {}
    rows: list[dict[str, Any]] = []
    if local:
        rows.append({"name": local.get("name") or "local", "local": True, "node": local})
    for peer in snap.get("peers") or []:
        node = peer.get("node") or {}
        if not node:
            continue
        rows.append({
            "name": peer.get("name") or node.get("name") or "peer",
            "local": False,
            "node": node,
            "seen_at": peer.get("node_seen_at"),
        })
    return rows


def _capability_index(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    providers: dict[str, list[str]] = {}
    for row in rows:
        name = str(row.get("name") or "node")
        node = row.get("node") or {}
        for capability, available in (node.get("capabilities") or {}).items():
            if available:
                providers.setdefault(str(capability), []).append(name)

        # Model-advertised features are capabilities too, but keep their namespace
        # explicit so a renderer never confuses "vision model exists" with camera I/O.
        for model in ((node.get("inference") or {}).get("models") or []):
            model_name = str(model.get("name") or "")
            caps = model.get("declared") or model.get("capabilities") or []
            if not caps and isinstance(model.get("features"), dict):
                caps = [key for key, value in model["features"].items() if value]
            if isinstance(caps, dict):
                caps = [key for key, value in caps.items() if value]
            if isinstance(caps, str):
                caps = [caps]
            for capability in caps:
                label = f"model.{capability}"
                entry = f"{name}:{model_name}" if model_name else name
                if entry not in providers.setdefault(label, []):
                    providers[label].append(entry)

    return [
        {"id": capability, "providers": names, "count": len(names)}
        for capability, names in sorted(providers.items())
    ]


def build_ui_model(data: dict[str, Any], *, mini: bool = False) -> dict[str, Any]:
    """Normalize Fabric snapshots into one renderer-neutral UI document."""
    rows = _node_rows(data)
    jobs = (data.get("jobs") or {}).get("jobs") or []
    active_jobs = [
        job for job in jobs
        if str(job.get("status") or "") not in {"ok", "done", "failed", "cancelled", "canceled"}
    ]
    events = (data.get("events") or {}).get("events") or []
    services = (data.get("services") or {}).get("services") or {}
    return {
        "schema": "fabric-ui-v1",
        "summary": {
            "node_count": len(rows),
            "active_jobs": len(active_jobs),
            "health_ok": bool((data.get("health") or {}).get("ok", False)),
        },
        "nodes": rows,
        "capabilities": _capability_index(rows),
        "jobs": active_jobs,
        "services": services,
        "recent": events,
        "actions": actions(mini=mini),
    }
