"""Small, dependency-free media library/session core for LOOK.

The core owns queue/library meaning. Playback engines and terminal/web UIs are edges.
Nothing here opens devices, starts players, or talks to Fabric.
"""
from __future__ import annotations

import hashlib
import json
import mimetypes
import os
import random
import re
import time
from pathlib import Path
from typing import Any, Iterable

SCHEMA_LIBRARY = "look-media-library-v1"
SCHEMA_SESSION = "look-media-session-v1"
SCHEMA_PLAYLIST = "look-media-playlist-v1"

AUDIO_EXTENSIONS = {
    ".aac", ".aif", ".aiff", ".alac", ".ape", ".caf", ".dff", ".dsf",
    ".flac", ".m4a", ".m4b", ".m4p", ".mka", ".mp2", ".mp3", ".mpc",
    ".oga", ".ogg", ".opus", ".spx", ".tta", ".wav", ".wma", ".wv",
}
VIDEO_EXTENSIONS = {
    ".3gp", ".avi", ".flv", ".m2ts", ".m4v", ".mkv", ".mov", ".mp4",
    ".mpeg", ".mpg", ".mts", ".ts", ".vob", ".webm", ".wmv",
}
MEDIA_EXTENSIONS = AUDIO_EXTENSIONS | VIDEO_EXTENSIONS

_TRACK_PREFIX = re.compile(r"^\s*(\d{1,3})(?:\s*[-._)]\s*|\s+)(.+?)\s*$")
_DISC_PREFIX = re.compile(r"^\s*(\d)[-_.](\d{1,3})(?:\s*[-._)]\s*|\s+)(.+?)\s*$")
_SAFE_NAME = re.compile(r"[^A-Za-z0-9._ -]+")


def _now() -> float:
    return time.time()


def _stable_id(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8", "surrogatepass")).hexdigest()[:16]


def _media_type(path: Path) -> str:
    guessed, _ = mimetypes.guess_type(str(path))
    if guessed:
        return guessed
    if path.suffix.casefold() in AUDIO_EXTENSIONS:
        return "audio/unknown"
    if path.suffix.casefold() in VIDEO_EXTENSIONS:
        return "video/unknown"
    return "application/octet-stream"


def _title_and_track(stem: str) -> tuple[str, int | None, int | None]:
    disc = None
    track = None
    title = stem.strip()
    match = _DISC_PREFIX.match(title)
    if match:
        disc = int(match.group(1))
        track = int(match.group(2))
        title = match.group(3).strip()
        return title, track, disc
    match = _TRACK_PREFIX.match(title)
    if match:
        track = int(match.group(1))
        title = match.group(2).strip()
    return title, track, disc


def entry_from_path(path: str | Path, root: str | Path | None = None) -> dict[str, Any]:
    """Create a cheap catalog row from filesystem structure, without hashing media bytes."""
    target = Path(path).expanduser().resolve()
    stat = target.stat()
    title, track, disc = _title_and_track(target.stem)

    rel_parts: tuple[str, ...] = ()
    root_path: Path | None = None
    if root is not None:
        try:
            root_path = Path(root).expanduser().resolve()
            rel_parts = target.relative_to(root_path).parts
        except (OSError, ValueError):
            rel_parts = ()

    artist = ""
    album = ""
    if root_path is not None:
        if len(rel_parts) >= 3:
            artist = rel_parts[-3]
            album = rel_parts[-2]
        elif len(rel_parts) >= 2:
            album = rel_parts[-2]
    else:
        album = target.parent.name
        if target.parent.parent != target.parent:
            artist = target.parent.parent.name

    return {
        "id": _stable_id(str(target)),
        "path": str(target),
        "root": str(root_path) if root_path else "",
        "artist": artist,
        "album": album,
        "title": title or target.stem,
        "track": track,
        "disc": disc,
        "format": target.suffix.casefold().lstrip("."),
        "media_type": _media_type(target),
        "bytes": stat.st_size,
        "mtime": stat.st_mtime,
    }


def empty_library() -> dict[str, Any]:
    return {"schema": SCHEMA_LIBRARY, "updated": 0.0, "roots": [], "entries": []}


def normalize_library(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        return empty_library()
    roots = [str(x) for x in (data.get("roots") or []) if str(x).strip()]
    entries = [dict(x) for x in (data.get("entries") or []) if isinstance(x, dict) and x.get("path")]
    return {
        "schema": SCHEMA_LIBRARY,
        "updated": float(data.get("updated") or 0.0),
        "roots": sorted(set(roots), key=str.casefold),
        "entries": entries,
    }


def scan_root(root: str | Path, existing: Any = None) -> dict[str, Any]:
    """Fast recursive media scan. Existing rows for other roots are preserved.

    This intentionally avoids codec probing and full-file hashing so a 10k-track
    library scan remains a filesystem operation rather than a media workload.
    """
    base = Path(root).expanduser().resolve()
    if not base.is_dir():
        raise NotADirectoryError(base)
    library = normalize_library(existing)
    base_s = str(base)

    current_rows = [row for row in library["entries"] if str(row.get("root") or "") == base_s]
    existing_by_path = {str(row.get("path") or ""): row for row in current_rows}
    keep = [row for row in library["entries"] if str(row.get("root") or "") != base_s]
    found: list[dict[str, Any]] = []
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = sorted((d for d in dirnames if not d.startswith(".")), key=str.casefold)
        for name in sorted(filenames, key=str.casefold):
            if name.startswith("."):
                continue
            path = Path(dirpath) / name
            if path.suffix.casefold() not in MEDIA_EXTENSIONS:
                continue
            try:
                row = entry_from_path(path, base)
                previous = existing_by_path.get(str(row.get("path") or "")) or {}
                # A rescan must not throw away expensive content identity. Preserve it
                # only when the cheap filesystem fingerprint still matches.
                if (previous.get("digest")
                        and int(previous.get("bytes") or -1) == int(row.get("bytes") or -2)
                        and float(previous.get("mtime") or -1) == float(row.get("mtime") or -2)):
                    row["digest"] = previous["digest"]
                    if previous.get("identified_at"):
                        row["identified_at"] = previous["identified_at"]
                found.append(row)
            except (FileNotFoundError, PermissionError, OSError):
                continue

    library["entries"] = sorted(keep + found, key=entry_sort_key)
    roots = [r for r in library["roots"] if r != base_s]
    roots.append(base_s)
    library["roots"] = sorted(set(roots), key=str.casefold)
    library["updated"] = _now()
    return library


def entry_sort_key(row: dict[str, Any]) -> tuple[Any, ...]:
    track = row.get("track")
    disc = row.get("disc")
    return (
        str(row.get("artist") or "").casefold(),
        str(row.get("album") or "").casefold(),
        int(disc) if isinstance(disc, int) else 0,
        int(track) if isinstance(track, int) else 9999,
        str(row.get("title") or "").casefold(),
        str(row.get("path") or "").casefold(),
    )


def _haystack(row: dict[str, Any]) -> str:
    return " ".join(str(row.get(k) or "") for k in ("artist", "album", "title", "path", "format")).casefold()


def search_entries(library: Any, query: str) -> list[dict[str, Any]]:
    rows = normalize_library(library)["entries"]
    tokens = [x.casefold() for x in query.split() if x.strip()]
    if not tokens:
        return list(rows)
    return [row for row in rows if all(token in _haystack(row) for token in tokens)]


def _artist_key(value: str) -> str:
    """Normalize conversational artist names without changing stored metadata."""
    key = " ".join(str(value or "").casefold().split())
    return key[4:] if key.startswith("the ") else key


def resolve_query(library: Any, query: str) -> list[dict[str, Any]]:
    """Resolve human media text with useful album/artist/title grouping before fuzzy rows."""
    rows = normalize_library(library)["entries"]
    q = query.strip().casefold()
    if not q:
        return []
    exact_album = [r for r in rows if str(r.get("album") or "").casefold() == q]
    if exact_album:
        return sorted(exact_album, key=entry_sort_key)
    artist_q = _artist_key(query)
    exact_artist = [r for r in rows if _artist_key(str(r.get("artist") or "")) == artist_q]
    if exact_artist:
        return sorted(exact_artist, key=entry_sort_key)
    exact_title = [r for r in rows if str(r.get("title") or "").casefold() == q]
    if exact_title:
        return sorted(exact_title, key=entry_sort_key)
    return sorted(search_entries(library, query), key=entry_sort_key)


def entries_under(library: Any, directory: str | Path) -> list[dict[str, Any]]:
    base = Path(directory).expanduser().resolve()
    out: list[dict[str, Any]] = []
    for row in normalize_library(library)["entries"]:
        try:
            Path(str(row.get("path") or "")).resolve().relative_to(base)
        except (ValueError, OSError):
            continue
        out.append(row)
    return sorted(out, key=entry_sort_key)


def queue_entry(row: dict[str, Any]) -> dict[str, Any]:
    allowed = ("id", "path", "node", "digest", "artist", "album", "title", "track", "disc", "format", "media_type", "bytes", "locations")
    out = {key: row.get(key) for key in allowed if row.get(key) not in (None, "")}
    if not out.get("id"):
        locator = str(out.get("path") or out.get("digest") or json.dumps(out, sort_keys=True))
        out["id"] = _stable_id(locator)
    return out


def merge_catalog_entries(rows: Iterable[dict[str, Any]], *, local_node: str = "") -> list[dict[str, Any]]:
    """Merge an online Fabric catalog into logical media rows.

    SHA identity collapses duplicate physical copies. Unidentified discoveries stay
    node-local until their bytes have been hashed. A local location is preferred so
    playback does not cross the network when the bytes are already here.
    """
    grouped: dict[str, list[dict[str, Any]]] = {}
    for raw in rows:
        if not isinstance(raw, dict):
            continue
        row = dict(raw)
        digest = str(row.get("digest") or "").strip()
        node = str(row.get("node") or "").strip()
        rid = str(row.get("id") or row.get("path") or "").strip()
        key = f"sha:{digest}" if digest else f"loc:{node}:{rid}"
        grouped.setdefault(key, []).append(row)

    merged: list[dict[str, Any]] = []
    for copies in grouped.values():
        copies.sort(key=lambda r: (0 if local_node and str(r.get("node") or "") == local_node else 1, entry_sort_key(r)))
        primary = dict(copies[0])
        locations = []
        for row in copies:
            locations.append({k: row.get(k) for k in ("node", "path", "id", "digest") if row.get(k) not in (None, "")})
        primary["locations"] = locations
        primary["copies"] = len(locations)
        merged.append(primary)
    return sorted(merged, key=entry_sort_key)


def completion_candidates(rows: Iterable[dict[str, Any]], query: str = "", *, limit: int = 80) -> list[str]:
    """Small human vocabulary for shell completion; never expose paths as titles."""
    q = query.strip().casefold()
    values: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        for key in ("artist", "album", "title"):
            value = str(row.get(key) or "").strip()
            if value and (not q or q in value.casefold()):
                values.add(value)
    def rank(value: str) -> tuple[int, int, str]:
        folded = value.casefold()
        if not q:
            tier = 2
        elif folded.startswith(q):
            tier = 0
        elif any(part.startswith(q) for part in folded.split()):
            tier = 1
        else:
            tier = 2
        return (tier, len(value), folded)
    return sorted(values, key=rank)[:max(1, int(limit))]


def new_session(entries: Iterable[dict[str, Any]], *, current_index: int = 0,
                shuffle: bool = False, repeat: str = "off", seed: int | None = None) -> dict[str, Any]:
    queue = [queue_entry(row) for row in entries]
    if shuffle and len(queue) > 1:
        rng = random.Random(seed)
        rng.shuffle(queue)
    if queue:
        current_index = max(0, min(int(current_index), len(queue) - 1))
    else:
        current_index = 0
    return {
        "schema": SCHEMA_SESSION,
        "id": f"media-{int(_now())}-{_stable_id(str(_now()))[:6]}",
        "queue": queue,
        "current_index": current_index,
        "state": "stopped",
        "shuffle": bool(shuffle),
        "repeat": repeat if repeat in {"off", "all"} else "off",
        "created": _now(),
        "updated": _now(),
    }


def normalize_session(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        return new_session([])
    queue = [queue_entry(x) for x in (data.get("queue") or []) if isinstance(x, dict)]
    idx = int(data.get("current_index") or 0)
    if queue:
        idx = max(0, min(idx, len(queue) - 1))
    else:
        idx = 0
    out = dict(data)
    out.update({
        "schema": SCHEMA_SESSION,
        "queue": queue,
        "current_index": idx,
        "state": str(data.get("state") or "stopped"),
        "shuffle": bool(data.get("shuffle", False)),
        "repeat": str(data.get("repeat") or "off") if str(data.get("repeat") or "off") in {"off", "all"} else "off",
        "updated": float(data.get("updated") or _now()),
    })
    return out


def playlist_name(name: str) -> str:
    cleaned = _SAFE_NAME.sub("", name).strip().replace(" ", "-")
    cleaned = re.sub(r"-+", "-", cleaned).strip("-.")
    if not cleaned:
        raise ValueError("playlist name is empty")
    return cleaned[:80]


def playlist_payload(name: str, session: Any) -> dict[str, Any]:
    normalized = normalize_session(session)
    return {
        "schema": SCHEMA_PLAYLIST,
        "name": name.strip(),
        "saved": _now(),
        "queue": normalized["queue"],
    }
