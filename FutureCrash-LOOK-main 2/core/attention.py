"""Pure attention-routing policy.

Attention is an event, not a speech call.  This module decides *where* a
requested channel may go; node.py owns effects and transport.
"""
from __future__ import annotations

CHANNELS = {"voice", "sound", "visual", "beacon"}
IMPORTANCE = {"low", "normal", "important", "urgent"}
DEFERRED_TARGETS = {"active", "follow-me"}


def normalize_event(payload: dict | None) -> dict:
    raw = dict(payload or {})
    message = " ".join(str(raw.get("message") or "").split())
    if not message:
        raise ValueError("attention message required")
    if len(message) > 1200:
        raise ValueError("attention message is limited to 1200 characters")
    channels = raw.get("channels") or ["voice"]
    if isinstance(channels, str):
        channels = [x.strip() for x in channels.split(",") if x.strip()]
    channels = [str(x).casefold() for x in channels]
    unknown = sorted(set(channels) - CHANNELS)
    if unknown:
        raise ValueError("unknown attention channel: " + ", ".join(unknown))
    importance = str(raw.get("importance") or "normal").casefold()
    if importance not in IMPORTANCE:
        raise ValueError("invalid attention importance: " + importance)
    target = str(raw.get("target") or "origin").strip() or "origin"
    if target.casefold() == "current":
        target = "origin"
    return {
        "schema": "fabric-attention-v1",
        "type": str(raw.get("type") or "attention")[:64],
        "message": message,
        "importance": importance,
        "source": str(raw.get("source") or "")[:120],
        "channels": channels,
        "target": target,
        "voice_profile": str(raw.get("voice_profile") or "default").casefold(),
    }


def _node_name(row: dict) -> str:
    return str(row.get("name") or ((row.get("identity") or {}).get("name")) or "").strip()


def _endpoint_values(row: dict) -> list[str]:
    metadata = row.get("metadata") or {}
    return [str(row.get("endpoint_id") or ""), str(row.get("label") or ""),
            str(row.get("surface") or ""), str(metadata.get("device") or "")]


def plan_voice_targets(event: dict, *, local_node: str, nodes: list[dict], endpoints: list[dict]) -> dict:
    """Return deterministic delivery candidates without performing effects.

    `active` and `follow-me` are intentionally unresolved until Fabric has
    trustworthy ephemeral presence evidence.  Never guess where the user is.
    """
    target = str(event.get("target") or "origin").strip()
    low = target.casefold().lstrip("@")
    local = str(local_node or "local")
    node_rows = []
    seen = set()
    for row in list(nodes or []):
        name = _node_name(row)
        if not name or name.casefold() in seen:
            continue
        seen.add(name.casefold())
        caps = row.get("capabilities") or {}
        if isinstance(caps, list):
            can_speak = "audio.speak" in caps
        else:
            can_speak = bool(caps.get("audio.speak"))
        if can_speak:
            node_rows.append({"kind": "node", "target": name, "label": name})
    endpoint_rows = []
    for row in endpoints or []:
        caps = set(row.get("capabilities") or [])
        if "audio.speak" in caps:
            endpoint_rows.append({"kind": "endpoint", "target": str(row.get("endpoint_id") or ""),
                                  "label": str(row.get("label") or row.get("endpoint_id") or "browser"),
                                  "row": row})

    if low in DEFERRED_TARGETS:
        return {"status": "presence-unresolved", "policy": low, "targets": [],
                "reason": "Fabric has no trusted active-device presence resolver yet"}
    if low in {"origin", "local"}:
        return {"status": "ready", "policy": "origin", "targets":
                [{"kind": "node", "target": local, "label": local}]}
    if low == "all":
        return {"status": "ready", "policy": "all", "targets": node_rows + endpoint_rows}

    exact_nodes = [r for r in node_rows if r["target"].casefold() == low]
    matches = list(exact_nodes)
    for row in endpoint_rows:
        vals = [v.casefold() for v in _endpoint_values(row["row"]) if v]
        if any(low == v or (len(low) >= 4 and low in v) for v in vals):
            matches.append(row)
    if not matches:
        return {"status": "not-found", "policy": "named", "targets": [],
                "reason": f"no speech-capable Fabric target matches {target!r}"}
    if len(matches) > 1:
        return {"status": "ambiguous", "policy": "named", "targets": [],
                "reason": f"attention target {target!r} is ambiguous"}
    return {"status": "ready", "policy": "named", "targets": matches}
