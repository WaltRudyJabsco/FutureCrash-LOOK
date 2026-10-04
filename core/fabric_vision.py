#!/usr/bin/env python3
"""User-initiated screen capture for Fabric Vision.

This module intentionally has no scheduler and no persistent store. A caller asks
for one frame; the endpoint captures one frame, returns bytes/metadata, and deletes
the temporary files. Repeated observation belongs to the requesting client.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import platform
import shutil
import subprocess
import sys
import tempfile
import socket
import time
from pathlib import Path

MAX_FRAME_BYTES = 6 * 1024 * 1024
DEFAULT_MAX_WIDTH = 1600
DEFAULT_QUALITY = 72


VISION_BROKER_SOCKET = Path.home()/".local/state/future-crash-look/vision-arm.sock"

def _broker_socket_path() -> Path:
    return VISION_BROKER_SOCKET

def vision_broker_request(*, previous_hash="", max_width=DEFAULT_MAX_WIDTH, quality=DEFAULT_QUALITY, display="main", timeout=8.0):
    """Ask an explicitly armed foreground capture broker for one frame.

    The broker exists only while `lk vision arm` is running in an authorized user
    terminal. This lets macOS keep Screen Recording permission attached to the
    foreground user process instead of granting the always-on node daemon capture
    authority.
    """
    path=_broker_socket_path()
    if not path.exists():
        raise FileNotFoundError("Fabric Vision is not armed on this Mac; run `lk vision arm 10m` locally")
    request={"previous_hash":str(previous_hash or ""),"max_width":int(max_width),"quality":int(quality),"display":str(display or "main")}
    data=(json.dumps(request,separators=(",",":"))+"\n").encode("utf-8")
    client=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
    client.settimeout(float(timeout))
    try:
        client.connect(str(path)); client.sendall(data)
        chunks=[]
        while True:
            part=client.recv(256*1024)
            if not part: break
            chunks.append(part)
            if sum(map(len,chunks)) > MAX_FRAME_BYTES*2: raise RuntimeError("vision broker response too large")
        payload=json.loads(b"".join(chunks).decode("utf-8","replace") or "{}")
    finally:
        client.close()
    if not isinstance(payload,dict): raise RuntimeError("invalid vision broker response")
    return payload

def run_vision_broker(duration=600.0):
    """Run a bounded foreground capture broker until timeout or Ctrl-C."""
    duration=max(5.0,min(3600.0,float(duration)))
    path=_broker_socket_path(); path.parent.mkdir(parents=True,exist_ok=True)
    try: path.unlink(missing_ok=True)
    except OSError: pass
    server=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
    server.bind(str(path)); os.chmod(path,0o600); server.listen(4); server.settimeout(.5)
    deadline=time.monotonic()+duration
    try:
        while time.monotonic() < deadline:
            try: conn,_=server.accept()
            except socket.timeout: continue
            with conn:
                conn.settimeout(5.0); raw=b""
                while b"\n" not in raw and len(raw)<64*1024:
                    chunk=conn.recv(8192)
                    if not chunk: break
                    raw+=chunk
                try:
                    req=json.loads(raw.split(b"\n",1)[0].decode("utf-8","replace") or "{}")
                    payload=capture_screen(previous_hash=str(req.get("previous_hash") or ""), max_width=int(req.get("max_width") or DEFAULT_MAX_WIDTH), quality=int(req.get("quality") or DEFAULT_QUALITY), display=req.get("display") or "main")
                except Exception as exc:
                    payload={"ok":False,"error":str(exc)}
                conn.sendall(json.dumps(payload,separators=(",",":"),ensure_ascii=False).encode("utf-8"))
    finally:
        server.close()
        try: path.unlink(missing_ok=True)
        except OSError: pass


def _which(*names: str) -> str | None:
    for name in names:
        if os.path.isabs(name) and os.access(name, os.X_OK):
            return name
        found = shutil.which(name)
        if found:
            return found
    return None


def _linux_wayland() -> bool:
    """Return whether this process belongs to a Wayland desktop session."""
    session = str(os.environ.get("XDG_SESSION_TYPE") or "").strip().lower()
    return session == "wayland" or bool(os.environ.get("WAYLAND_DISPLAY"))


def _portal_python() -> str | None:
    """Find a Python with PyGObject so we can use the desktop screenshot portal."""
    candidates = []
    if sys.executable:
        candidates.append(sys.executable)
    if "/usr/bin/python3" not in candidates:
        candidates.append("/usr/bin/python3")
    for python in candidates:
        if not os.path.exists(python):
            continue
        try:
            probe = subprocess.run(
                [python, "-c", "from gi.repository import Gio, GLib"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=2,
            )
        except (OSError, subprocess.TimeoutExpired):
            continue
        if probe.returncode == 0:
            return python
    return None



def list_displays() -> list[dict]:
    """Best-effort stable display inventory for user-directed capture."""
    system = platform.system().lower()
    rows = []
    if system == "darwin":
        profiler = _which("/usr/sbin/system_profiler", "system_profiler")
        if profiler:
            try:
                cp = subprocess.run([profiler, "SPDisplaysDataType", "-json"], capture_output=True, text=True, timeout=8)
                data = json.loads(cp.stdout or "{}") if cp.returncode == 0 else {}
                for gpu in data.get("SPDisplaysDataType") or []:
                    for d in gpu.get("spdisplays_ndrvs") or []:
                        idx = len(rows) + 1
                        rows.append({
                            "index": idx,
                            "name": str(d.get("_name") or d.get("spdisplays_display_type") or f"Display {idx}"),
                            "resolution": str(d.get("_spdisplays_resolution") or d.get("spdisplays_resolution") or ""),
                            "main": str(d.get("spdisplays_main") or "").lower() in {"spdisplays_yes","yes","true"},
                            "capture_id": str(idx),
                        })
            except Exception:
                rows = []
    elif system == "linux":
        wlr = _which("wlr-randr")
        if wlr:
            try:
                cp = subprocess.run([wlr, "--json"], capture_output=True, text=True, timeout=4)
                data = json.loads(cp.stdout or "[]") if cp.returncode == 0 else []
                for item in data if isinstance(data, list) else []:
                    if not item.get("enabled", True):
                        continue
                    idx=len(rows)+1; mode=item.get("current_mode") or {}
                    rows.append({"index":idx,"name":str(item.get("name") or f"Display {idx}"),
                                 "resolution":f"{mode.get('width','')}x{mode.get('height','')}".strip('x'),
                                 "main":idx==1,"capture_id":str(item.get("name") or idx)})
            except Exception:
                rows=[]
        if not rows and os.environ.get("DISPLAY"):
            xrandr=_which("xrandr")
            if xrandr:
                try:
                    cp=subprocess.run([xrandr,"--query"],capture_output=True,text=True,timeout=4)
                    for line in (cp.stdout or "").splitlines():
                        m=re.match(r"^(\S+) connected(?: primary)? (\d+x\d+)",line)
                        if not m: continue
                        idx=len(rows)+1
                        rows.append({"index":idx,"name":m.group(1),"resolution":m.group(2),
                                     "main":" connected primary " in line,"capture_id":m.group(1)})
                except Exception:
                    rows=[]
    if not rows:
        rows=[{"index":1,"name":"Main display","resolution":"","main":True,"capture_id":"1"}]
    if not any(r.get("main") for r in rows): rows[0]["main"]=True
    return rows


def _resolve_display(display) -> dict:
    rows=list_displays()
    value=str(display or "main").strip()
    if value.casefold() in {"","main","primary","default"}:
        return next((r for r in rows if r.get("main")),rows[0])
    try: idx=int(value)
    except ValueError: idx=-1
    for row in rows:
        if row.get("index")==idx or str(row.get("name") or "").casefold()==value.casefold():
            return row
    raise ValueError(f"display {value!r} not found")

def capture_provider() -> dict:
    """Return the best screen-capture provider available on this node."""
    system = platform.system().lower()
    if system == "darwin":
        tool = _which("/usr/sbin/screencapture", "screencapture")
        if tool:
            return {"name": "screencapture", "tool": tool, "platform": "macos"}
        return {"name": "", "tool": "", "platform": "macos", "error": "screencapture not found"}

    if system == "linux":
        wayland = _linux_wayland()

        # Compositor-native tools come first. They avoid portal prompts where a
        # desktop exposes a direct, user-session capture utility.
        native = (
            ("grim", "grim"),
            ("gnome-screenshot", "gnome-screenshot"),
            ("spectacle", "spectacle"),
        )
        for name, binary in native:
            tool = _which(binary)
            if tool:
                return {"name": name, "tool": tool, "platform": "linux", "session": "wayland" if wayland else "x11"}

        if wayland:
            # ImageMagick import/scrot are X11 capture tools. On Wayland they can
            # emit the misleading "missing an image filename" error even though
            # the filename is present. The desktop portal is the generic Wayland
            # capture API and keeps permission in the compositor/user's hands.
            portal_python = _portal_python()
            if portal_python:
                return {"name": "xdg-desktop-portal", "tool": portal_python, "platform": "linux", "session": "wayland"}
            return {
                "name": "",
                "tool": "",
                "platform": "linux",
                "session": "wayland",
                "error": "Wayland screen capture needs grim, gnome-screenshot, Spectacle, or xdg-desktop-portal/PyGObject",
            }

        # X11 fallbacks are valid only when an X11 desktop is actually active.
        for name, binary in (("scrot", "scrot"), ("imagemagick-import", "import")):
            tool = _which(binary)
            if tool:
                return {"name": name, "tool": tool, "platform": "linux", "session": "x11"}

        # The portal is also a safe final fallback on X11 desktops that provide it.
        portal_python = _portal_python()
        if portal_python:
            return {"name": "xdg-desktop-portal", "tool": portal_python, "platform": "linux", "session": "x11"}
        return {"name": "", "tool": "", "platform": "linux", "error": "no supported screen capture tool found"}

    return {"name": "", "tool": "", "platform": system or "unknown", "error": "screen capture is not supported on this platform"}


def _capture_command(provider: dict, output: Path, display: dict | None = None) -> list[str]:
    name = provider.get("name")
    tool = str(provider.get("tool") or "")
    if name == "screencapture":
        cmd=[tool, "-x", "-t", "png"]
        if display: cmd.extend(["-D", str(display.get("index") or 1)])
        return cmd+[str(output)]
    if name == "grim":
        cmd=[tool]
        if display and display.get("capture_id"): cmd.extend(["-o",str(display.get("capture_id"))])
        return cmd+[str(output)]
    if name == "gnome-screenshot":
        return [tool, "-f", str(output)]
    if name == "spectacle":
        return [tool, "-b", "-n", "-o", str(output)]
    if name == "scrot":
        return [tool, str(output)]
    if name == "imagemagick-import":
        return [tool, "-window", "root", str(output)]
    raise RuntimeError("no screen capture provider")


_PORTAL_HELPER = r"""
from gi.repository import Gio, GLib
import sys, uuid

output = sys.argv[1]
connection = Gio.bus_get_sync(Gio.BusType.SESSION, None)
unique = (connection.get_unique_name() or "").lstrip(":").replace(".", "_")
token = "fabricvision_" + uuid.uuid4().hex
expected = "/org/freedesktop/portal/desktop/request/%s/%s" % (unique, token)
loop = GLib.MainLoop()
state = {"done": False, "error": "screenshot portal did not respond"}


def on_response(conn, sender, object_path, interface, signal, parameters, user_data):
    response, results = parameters.unpack()
    state["done"] = True
    if response == 0 and results.get("uri"):
        try:
            source = Gio.File.new_for_uri(results["uri"])
            dest = Gio.File.new_for_path(output)
            source.copy(dest, Gio.FileCopyFlags.OVERWRITE, None, None)
            state["error"] = ""
        except Exception as exc:
            state["error"] = str(exc)
    elif response == 1:
        state["error"] = "screen capture cancelled"
    else:
        state["error"] = "screenshot portal failed"
    loop.quit()


subscription = connection.signal_subscribe(
    "org.freedesktop.portal.Desktop",
    "org.freedesktop.portal.Request",
    "Response",
    expected,
    None,
    Gio.DBusSignalFlags.NONE,
    on_response,
    None,
)
proxy = Gio.DBusProxy.new_sync(
    connection,
    Gio.DBusProxyFlags.NONE,
    None,
    "org.freedesktop.portal.Desktop",
    "/org/freedesktop/portal/desktop",
    "org.freedesktop.portal.Screenshot",
    None,
)
options = {
    "handle_token": GLib.Variant("s", token),
    "interactive": GLib.Variant("b", False),
}
try:
    result = proxy.call_sync(
        "Screenshot",
        GLib.Variant("(sa{sv})", ("", options)),
        Gio.DBusCallFlags.NONE,
        12000,
        None,
    )
    returned = result.unpack()[0]
    if returned != expected:
        connection.signal_unsubscribe(subscription)
        subscription = connection.signal_subscribe(
            "org.freedesktop.portal.Desktop",
            "org.freedesktop.portal.Request",
            "Response",
            returned,
            None,
            Gio.DBusSignalFlags.NONE,
            on_response,
            None,
        )
except Exception as exc:
    print(str(exc), file=sys.stderr)
    raise SystemExit(2)


def timeout():
    state["error"] = "screenshot portal timed out"
    loop.quit()
    return False

GLib.timeout_add_seconds(12, timeout)
loop.run()
connection.signal_unsubscribe(subscription)
if state["error"]:
    print(state["error"], file=sys.stderr)
    raise SystemExit(2)
"""


def _capture_portal(provider: dict, output: Path) -> subprocess.CompletedProcess:
    """Capture through xdg-desktop-portal on the user's session bus."""
    return subprocess.run(
        [str(provider.get("tool") or "/usr/bin/python3"), "-c", _PORTAL_HELPER, str(output)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        timeout=15,
    )


def _compress(source: Path, dest: Path, max_width: int, quality: int) -> tuple[Path, str]:
    """Compress to WebP when ffmpeg is available; otherwise return the PNG."""
    ffmpeg = _which("ffmpeg", "/opt/homebrew/bin/ffmpeg", "/usr/local/bin/ffmpeg", "/home/linuxbrew/.linuxbrew/bin/ffmpeg")
    if not ffmpeg:
        return source, "image/png"
    width = max(320, min(3840, int(max_width or DEFAULT_MAX_WIDTH)))
    q = max(20, min(95, int(quality or DEFAULT_QUALITY)))
    # libwebp quality maps naturally to q:v for ffmpeg. Preserve aspect ratio and
    # never upscale a smaller desktop.
    vf = f"scale='min({width},iw)':-2"
    cmd = [ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", str(source), "-vf", vf, "-c:v", "libwebp", "-q:v", str(q), "-frames:v", "1", str(dest)]
    try:
        run = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=12)
        if run.returncode == 0 and dest.exists() and dest.stat().st_size > 0:
            return dest, "image/webp"
    except (OSError, subprocess.TimeoutExpired):
        pass
    return source, "image/png"


def capture_screen(*, previous_hash: str = "", max_width: int = DEFAULT_MAX_WIDTH, quality: int = DEFAULT_QUALITY, display: str | int = "main") -> dict:
    """Capture one screen frame and return a transport-ready ephemeral payload."""
    provider = capture_provider()
    if not provider.get("tool"):
        return {"ok": False, "available": False, "error": provider.get("error") or "screen capture unavailable", "provider": provider}

    try:
        selected=_resolve_display(display)
    except ValueError as exc:
        return {"ok":False,"available":True,"error":str(exc),"provider":provider,"displays":list_displays()}
    if str(display or "main").casefold() not in {"","main","primary","default","1"} and provider.get("name") not in {"screencapture","grim"}:
        return {"ok":False,"available":True,"error":f"{provider.get('name') or 'capture backend'} cannot target an individual display on this desktop", "provider":provider,"display":selected}

    with tempfile.TemporaryDirectory(prefix="fabric-vision-") as temp:
        root = Path(temp)
        raw = root / "screen.png"
        encoded = root / "screen.webp"
        try:
            if provider.get("name") == "xdg-desktop-portal":
                proc = _capture_portal(provider, raw)
            else:
                command=_capture_command(provider,raw,selected) if str(display or "main").casefold() not in {"","main","primary","default","1"} else _capture_command(provider,raw)
                proc = subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=12)
        except subprocess.TimeoutExpired:
            return {"ok": False, "available": True, "error": "screen capture timed out", "provider": provider}
        except OSError as exc:
            return {"ok": False, "available": True, "error": str(exc), "provider": provider}

        if proc.returncode != 0 or not raw.exists() or raw.stat().st_size == 0:
            detail = proc.stderr.decode("utf-8", "replace").strip()[:600]
            return {"ok": False, "available": True, "error": detail or f"{provider['name']} failed", "provider": provider}

        frame, mime = _compress(raw, encoded, max_width, quality)
        try:
            data = frame.read_bytes()
        except OSError as exc:
            return {"ok": False, "available": True, "error": str(exc), "provider": provider}

        if len(data) > MAX_FRAME_BYTES:
            return {"ok": False, "available": True, "error": f"captured frame exceeds {MAX_FRAME_BYTES // (1024*1024)} MiB transport limit", "provider": provider, "bytes": len(data)}

        digest = hashlib.sha256(data).hexdigest()
        unchanged = bool(previous_hash and previous_hash == digest)
        payload = {
            "ok": True,
            "available": True,
            "changed": not unchanged,
            "hash": digest,
            "mime": mime,
            "bytes": len(data),
            "provider": {k: provider.get(k) for k in ("name", "platform")},
            "ephemeral": True,
            "stored": False,
            "display": selected,
        }
        if not unchanged:
            payload["image_base64"] = base64.b64encode(data).decode("ascii")
        return payload
