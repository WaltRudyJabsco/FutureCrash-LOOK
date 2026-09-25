"""Deterministic natural-language intent normalization for common Fabric actions.

English belongs at the edge.  This module turns the small set of obvious,
low-ambiguity phrases into validated boring data.  Ambiguous language still
falls through to LO/model reasoning rather than growing a pile of magic rules.
"""
from __future__ import annotations

import re
from typing import Any

SCHEMA = "fabric-intent-v2"

_MEDIA_KIND = {
    "movie": "video", "movies": "video", "video": "video", "videos": "video",
    "film": "video", "films": "video",
    "music": "audio", "song": "audio", "songs": "audio", "track": "audio", "tracks": "audio",
}


def _clean(value: str) -> str:
    text = " ".join(str(value or "").strip().split())
    # Terminal transcripts sometimes carry LOOK's visible prompt glyph when a
    # command is pasted back into LO. Treat it as presentation, not language.
    return re.sub(r"^[›>]+\s*", "", text)


def _intent(action: str, **fields: Any) -> dict[str, Any]:
    out = {"schema": SCHEMA, "action": action}
    out.update({k: v for k, v in fields.items() if v not in (None, "")})
    return out


def normalize(prompt: str) -> dict[str, Any] | None:
    """Return a deterministic structured intent only when the phrase is obvious."""
    text = _clean(prompt)
    if not text:
        return None
    low = text.casefold().strip(" .!?")

    controls = {
        "pause": "pause", "pause music": "pause", "pause playback": "pause",
        "resume": "play", "resume music": "play", "resume playback": "play",
        "next": "next", "next track": "next", "next song": "next",
        "previous": "previous", "previous track": "previous", "previous song": "previous", "prev": "previous",
        "stop": "stop", "stop music": "stop", "stop playback": "stop",
    }
    if low in controls:
        return _intent("media.control", control=controls[low])

    # Explicit generic noun phrases are selectors, never catalog strings.
    # Keep this ahead of ordinary media lookup so "a song" cannot accidentally
    # become a queue of titles containing those words.
    m = re.fullmatch(
        r"(?:please\s+)?(?:play|put\s+on)\s+(?:me\s+)?"
        r"(?:a|an|any|some|random)\s+"
        r"(movie|movies|film|films|video|videos|music|song|songs|track|tracks)",
        low,
    )
    if m:
        return _intent("media.play", kind=_MEDIA_KIND[m.group(1)], selection="random", limit=1, match_mode="selector")

    # A few bare media nouns are conventional requests rather than plausible
    # titles. Quoting them below remains an explicit way to request a title.
    m = re.fullmatch(r"(?:please\s+)?(?:play|put\s+on)\s+(music|movie|movies|film|films|video|videos)", low)
    if m:
        return _intent("media.play", kind=_MEDIA_KIND[m.group(1)], selection="random", limit=1, match_mode="selector")

    # "play something by Talking Heads" is a selector over an artist rather
    # than a request for a title literally named "something".
    m = re.fullmatch(r"(?:please\s+)?(?:play|put\s+on)\s+(?:me\s+)?(?:something|anything|some\s+music)\s+by\s+(.+)", text, re.I)
    if m:
        artist = _clean(m.group(1).strip(" .!?"))
        if artist:
            return _intent("media.play", kind="audio", artist=artist, selection="random", limit=1)

    # Ordinary media requests are fuzzy by default. A visibly quoted target is
    # the conversational escape hatch for literal lookup; unlike a shell, LO
    # and Signal still have the original quote characters at this edge.
    m = re.fullmatch(r"(?:please\s+)?(play|shuffle|queue)\s+(.+?)\s*", text, re.I)
    if m:
        verb = m.group(1).casefold()
        raw = _clean(m.group(2).strip(" .!?"))
        literal = len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in {'\"', "'"}
        query = _clean(raw[1:-1] if literal else raw)
        if query:
            mode = "literal" if literal else "fuzzy"
            if verb == "queue":
                return _intent("media.queue", query=query, match_mode=mode)
            return _intent("media.play", query=query, shuffle=(verb == "shuffle"), match_mode=mode)
    return None


def resolve(prompt: str) -> dict[str, Any]:
    """Classify the cheap edge decision without pretending ambiguity is failure.

    `resolved` means the deterministic layer owns the request. `clarify` means a
    deictic request needs conversational/catalog context. `no_match` means the
    cheap layer declines it so LO can reason about it.
    """
    text = _clean(prompt)
    low = text.casefold().strip(" .!?")
    # Deictic targets need context. Catch them before the generic "play X" rule
    # can accidentally turn "that movie" into a literal catalog filename.
    if re.fullmatch(r"(?:please\s+)?(?:play|put\s+on|open|show)\s+(?:this|that|it|these|those)(?:\s+(?:movie|video|song|track|file|document))?", low):
        return {"status": "clarify", "reason": "referent_required"}
    intent = normalize(text)
    if intent is not None:
        return {"status": "resolved", "intent": intent}
    return {"status": "no_match"}


def media_tool(intent: dict[str, Any] | None) -> dict[str, Any] | None:
    """Translate normalized media intent into LOOK's existing tool contract."""
    if not isinstance(intent, dict):
        return None
    action = str(intent.get("action") or "")
    if action == "media.control":
        return {"tool": "media_control", "args": {"action": intent.get("control") or "status"}}
    if action == "media.queue":
        return {"tool": "media_queue", "args": {"query": intent.get("query") or ""}}
    if action == "media.play":
        args = {k: intent.get(k) for k in ("query", "kind", "artist", "selection", "limit", "shuffle") if intent.get(k) not in (None, "")}
        mode=intent.get("match_mode")
        if args.get("query") and mode in {"literal","fuzzy"}:
            args["match_mode"]=mode
        return {"tool": "media_play", "args": args}
    return None
