#!/usr/bin/env python3
"""Future Crash + LOOK Unified Node 4.1.

A small distributed supervisor for trusted personal machines. Immediate events stay
asynchronous; a one-second fabric pulse reconciles presence, leases and stale work.
"""
from __future__ import annotations

import argparse
import sys
import json
import os
import platform
import shutil
import socket
import subprocess
import threading
import time
import urllib.error
import urllib.request
import uuid
from dataclasses import asdict, dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

VERSION = "4.2.0"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 7332
PULSE_SECONDS = 1.0
PEER_REFRESH_SECONDS = 5.0
MODEL_REFRESH_SECONDS = 15.0
QUALIFY_RECHECK_SECONDS = 24 * 60 * 60
QUALIFY_IDLE_SECONDS = 20.0
INTERACTIVE_STALE_SECONDS = 45.0
BACKGROUND_STALE_SECONDS = 12.0
HISTORY_LIMIT = 64
PRIORITY = {"interactive": 0, "followup": 1, "background": 2}

STATE = Path.home() / ".local/share/future-crash-look"
STATE.mkdir(parents=True, exist_ok=True)
MODEL_STATE = STATE / "model_profiles.json"


def now() -> float:
    return time.time()


def pulse_number(t: float | None = None) -> int:
    """Wall-clock beat shared approximately across Tailscale/NTP-synchronised nodes."""
    return int((t if t is not None else now()) // PULSE_SECONDS)


def probe(host: str, port: int, timeout: float = .12) -> bool:
    try:
        with socket.create_connection((host, port), timeout):
            return True
    except OSError:
        return False


def run(*args: str, timeout: float = 1.5):
    try:
        return subprocess.run(args, text=True, capture_output=True, timeout=timeout)
    except Exception:
        return None


def binary(name: str) -> str | None:
    """Services have a smaller PATH than shells; inspect canonical user locations too."""
    found = shutil.which(name)
    if found:
        return found
    for p in (Path.home()/".local/bin"/name, Path.home()/"bin"/name,
              Path("/opt/homebrew/bin")/name, Path("/usr/local/bin")/name,
              Path("/usr/bin")/name):
        if p.exists() and os.access(p, os.X_OK):
            return str(p)
    return None


def http_json(url: str, data=None, timeout: float = 2.0):
    body = None if data is None else json.dumps(data).encode()
    req = urllib.request.Request(url, data=body,
        headers={"Content-Type": "application/json"} if body else {})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read() or b"{}")


@dataclass
class Lease:
    id: str
    owner: str
    priority: str
    phase: str
    detail: str
    started: float
    last_progress: float
    progress_count: int = 0
    state: str = "healthy"
    cancel_requested: bool = False
    worker: str = "local"

    def public(self):
        d = asdict(self)
        t = now()
        d["elapsed_ms"] = int((t - self.started) * 1000)
        d["idle_ms"] = int((t - self.last_progress) * 1000)
        d["started_pulse"] = pulse_number(self.started)
        d["progress_pulse"] = pulse_number(self.last_progress)
        return d


class Supervisor:
    def __init__(self):
        self.lock = threading.RLock()
        self.active: Lease | None = None
        self.history = []
        self.last_human_activity = now()

    def _archive(self, lease: Lease, status: str, detail: str):
        d = lease.public()
        d.update(status=status, finished=now(), final_detail=detail,
                 finished_pulse=pulse_number())
        self.history.append(d)
        self.history = self.history[-HISTORY_LIMIT:]

    def acquire(self, owner, priority="interactive", phase="accepted", detail="", worker="local"):
        priority = priority if priority in PRIORITY else "interactive"
        with self.lock:
            if priority != "background":
                self.last_human_activity = now()
            if self.active:
                # Human work has eminent domain. Background work is asked to yield and
                # immediately loses the logical lane; its executor observes cancellation.
                if PRIORITY[priority] < PRIORITY[self.active.priority] and self.active.priority == "background":
                    old = self.active
                    old.cancel_requested = True
                    old.state = "preempted"
                    self._archive(old, "preempted", f"yielded to {owner}")
                    self.active = None
                else:
                    return None, self.active.public()
            t = now()
            self.active = Lease(uuid.uuid4().hex[:12], str(owner), priority,
                                str(phase), str(detail), t, t, worker=str(worker))
            return self.active.public(), None

    def progress(self, rid, phase=None, detail=None):
        with self.lock:
            if not self.active or self.active.id != rid:
                return False
            if phase:
                self.active.phase = str(phase)
            if detail is not None:
                self.active.detail = str(detail)
            self.active.last_progress = now()
            self.active.progress_count += 1
            self.active.state = "healthy"
            return True

    def release(self, rid, status="ok", detail=""):
        with self.lock:
            if not self.active or self.active.id != rid:
                return False
            self._archive(self.active, str(status), str(detail))
            self.active = None
            return True

    def cancelled(self, rid):
        with self.lock:
            return bool(self.active and self.active.id == rid and self.active.cancel_requested)

    def reconcile(self):
        """Pulse backstop: mark stale work; never kill healthy work on elapsed time alone."""
        with self.lock:
            if not self.active:
                return
            idle = now() - self.active.last_progress
            stale_after = BACKGROUND_STALE_SECONDS if self.active.priority == "background" else INTERACTIVE_STALE_SECONDS
            if idle >= stale_after:
                self.active.state = "stale"
            elif idle >= stale_after / 2:
                self.active.state = "quiet"
            else:
                self.active.state = "healthy"

    def status(self):
        with self.lock:
            return {"active": self.active.public() if self.active else None,
                    "recent": self.history[-8:]}


SUP = Supervisor()


def tailscale_self():
    ts = binary("tailscale")
    if not ts:
        return {}
    p = run(ts, "status", "--json", timeout=2)
    if not p or p.returncode:
        return {}
    try:
        d = json.loads(p.stdout)
        me = d.get("Self") or {}
        dns = (me.get("DNSName") or "").rstrip(".")
        return {"hostname": me.get("HostName") or "", "dns": dns,
                "ips": me.get("TailscaleIPs") or [], "online": bool(me.get("Online", True))}
    except Exception:
        return {}


def identity():
    ts = tailscale_self()
    # Tailscale hostname is the stable human network identity when available.
    name = ((ts.get("dns") or "").split(".", 1)[0] or ts.get("hostname") or socket.gethostname())
    return {"name": name, "hostname": socket.gethostname(), "tailscale": ts}


def capabilities():
    lk = binary("lk")
    return {
        "filesystem": True,
        "shell": True,
        "look": bool(lk),
        # LO is currently an interface implemented by LOOK even when no standalone
        # `lo` executable exists in a service's PATH.
        "lo": bool(binary("lo") or lk),
        "tailscale": bool(binary("tailscale")),
        "ollama": probe("127.0.0.1", 11434),
        "signal": probe("127.0.0.1", 7331),
        "node": True,
        "comfyui": probe("127.0.0.1", 8188),
        "mercury": probe("127.0.0.1", 8888),
    }


def load_profiles():
    try:
        d = json.loads(MODEL_STATE.read_text())
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def save_profiles(d):
    tmp = MODEL_STATE.with_suffix(".tmp")
    tmp.write_text(json.dumps(d, indent=2, sort_keys=True) + "\n")
    os.chmod(tmp, 0o600)
    tmp.replace(MODEL_STATE)


class ModelRegistry:
    def __init__(self):
        self.lock = threading.RLock()
        self.cached_at = 0.0
        self.cached = []
        self.profiles = load_profiles()

    def _show(self, name):
        try:
            return http_json("http://127.0.0.1:11434/api/show", {"model": name}, timeout=2)
        except Exception:
            return {}

    def discover(self, force=False):
        with self.lock:
            if not force and now() - self.cached_at < MODEL_REFRESH_SECONDS:
                return self.cached
            if not probe("127.0.0.1", 11434):
                self.cached, self.cached_at = [], now()
                return []
            try:
                tags = http_json("http://127.0.0.1:11434/api/tags", timeout=2).get("models") or []
                ps = http_json("http://127.0.0.1:11434/api/ps", timeout=2).get("models") or []
            except Exception:
                return self.cached
            resident = {str(x.get("name") or x.get("model") or ""): x for x in ps}
            out = []
            for item in tags:
                name = str(item.get("name") or item.get("model") or "")
                if not name:
                    continue
                show = self._show(name)
                declared = show.get("capabilities") or []
                if isinstance(declared, str):
                    declared = [declared]
                declared = sorted({str(x).lower() for x in declared})
                # Ollama's declaration is authoritative where present. Keep raw values
                # and expose convenient booleans without inventing quality scores.
                features = {
                    "text": "completion" in declared or not declared,
                    "vision": "vision" in declared,
                    "tools": "tools" in declared,
                    "thinking": "thinking" in declared,
                    "embedding": "embedding" in declared,
                }
                profile = self.profiles.get(name) or {}
                out.append({
                    "name": name,
                    "size": item.get("size"),
                    "modified_at": item.get("modified_at"),
                    "family": ((show.get("details") or {}).get("family") or (item.get("details") or {}).get("family")),
                    "parameter_size": ((show.get("details") or {}).get("parameter_size") or (item.get("details") or {}).get("parameter_size")),
                    "quantization": ((show.get("details") or {}).get("quantization_level") or (item.get("details") or {}).get("quantization_level")),
                    "declared": declared,
                    "features": features,
                    "resident": name in resident,
                    "resident_size": (resident.get(name) or {}).get("size_vram"),
                    "qualification": profile.get("qualification"),
                })
            self.cached, self.cached_at = out, now()
            return out

    def record_qualification(self, name, result):
        with self.lock:
            self.profiles.setdefault(name, {})["qualification"] = result
            save_profiles(self.profiles)
            self.cached_at = 0


MODELS = ModelRegistry()


def peer_rows():
    ts = binary("tailscale")
    if not ts:
        return []
    p = run(ts, "status", "--json", timeout=2)
    if not p or p.returncode:
        return []
    try:
        d = json.loads(p.stdout)
    except Exception:
        return []
    result = []
    for peer in (d.get("Peer") or {}).values():
        dns = (peer.get("DNSName") or "").rstrip(".")
        ips = peer.get("TailscaleIPs") or []
        # DNS labels are tailnet-unique and avoid generic hostnames such as
        # "localhost" appearing as duplicate peers in the fabric view.
        name = (dns.split(".", 1)[0] if dns else "") or peer.get("HostName") or (ips[0] if ips else "peer")
        result.append({"name": name, "dns": dns, "ips": ips, "online": bool(peer.get("Online"))})
    return sorted(result, key=lambda x: (not x["online"], x["name"].lower()))


class PeerRegistry:
    def __init__(self):
        self.lock = threading.RLock()
        self.rows = []
        self.last_refresh = 0.0

    def refresh(self):
        rows = peer_rows()
        enriched = []
        for p in rows:
            q = dict(p)
            q["node"] = None
            if p["online"] and p["dns"]:
                try:
                    # Published node APIs use Tailscale HTTPS. Failure simply means the
                    # peer is not yet a Future Crash node or has no :7332 publication.
                    q["node"] = http_json(f"https://{p['dns']}:7332/v1/advertisement", timeout=.7)
                except Exception:
                    pass
            enriched.append(q)
        with self.lock:
            self.rows, self.last_refresh = enriched, now()

    def public(self):
        with self.lock:
            return list(self.rows)


PEERS = PeerRegistry()


def advertisement():
    ident = identity()
    models = MODELS.discover()
    return {
        "protocol": 1,
        "version": VERSION,
        "pulse": {"epoch": "unix-1s-v1", "number": pulse_number(), "period_ms": int(PULSE_SECONDS*1000)},
        "identity": ident,
        "platform": {"system": platform.system().lower(), "architecture": platform.machine()},
        "capabilities": capabilities(),
        "inference": {
            "available": bool(models),
            "models": models,
            "resident": [m["name"] for m in models if m.get("resident")],
        },
        "supervisor": SUP.status(),
    }


def node_info():
    ad = advertisement()
    return {"name": ad["identity"]["name"], "hostname": ad["identity"]["hostname"],
            "version": VERSION, "platform": ad["platform"]["system"],
            "architecture": ad["platform"]["architecture"],
            "pulse": ad["pulse"], "capabilities": ad["capabilities"],
            "inference": ad["inference"], "supervisor": ad["supervisor"]}


def qualify_model(name: str, automatic=False):
    """Tiny operational qualification. It tests only a resident model automatically.

    Active qualification streams a very short deterministic response so preemption can
    close the HTTP response quickly. It is evidence about this node, not an IQ score.
    """
    models = {m["name"]: m for m in MODELS.discover(force=True)}
    m = models.get(name)
    if not m:
        return {"ok": False, "error": "model not installed"}
    if automatic and not m.get("resident"):
        return {"ok": False, "skipped": "automatic qualification never cold-loads a model"}
    lease, busy = SUP.acquire(f"qualify:{name}", "background", "qualifying", "tiny model self-test")
    if not lease:
        return {"ok": False, "skipped": "supervisor busy", "busy": busy}
    rid = lease["id"]
    started = now()
    first = None
    content = ""
    eval_count = None
    eval_duration = None
    done_seen = False
    thinking = ""
    try:
        payload = {
            "model": name,
            "messages": [{"role": "user", "content": "Reply with exactly: READY"}],
            "stream": True,
            "think": False,
            "keep_alive": -1,
            "options": {"temperature": 0, "num_predict": 8},
        }
        req = urllib.request.Request("http://127.0.0.1:11434/api/chat",
                                     data=json.dumps(payload).encode(),
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as r:
            for raw in r:
                if SUP.cancelled(rid):
                    raise InterruptedError("preempted by interactive work")
                if not raw.strip():
                    continue
                obj = json.loads(raw)
                msg = obj.get("message") or {}
                piece = str(msg.get("content") or "")
                thought = str(msg.get("thinking") or "")
                if (piece or thought) and first is None:
                    first = now()
                content += piece
                thinking += thought
                if obj.get("done"):
                    done_seen = True
                    eval_count = obj.get("eval_count")
                    eval_duration = obj.get("eval_duration")
                SUP.progress(rid, "qualifying", "model produced progress")
        ended = now()
        tok_s = None
        if eval_count and eval_duration:
            tok_s = round(float(eval_count) / (float(eval_duration) / 1e9), 2)
        instruction_ok = content.strip().upper().startswith("READY")
        # Qualification answers two questions separately: did inference operate, and
        # did this tiny instruction-following probe comply? Thinking-only models no
        # longer get mislabeled as operational failures.
        result = {
            "ok": bool(done_seen and (eval_count or content or thinking)),
            "instruction_ok": instruction_ok,
            "tested_at": ended,
            "automatic": bool(automatic),
            "warm": bool(m.get("resident")),
            "ttft_ms": int(((first or ended) - started) * 1000),
            "total_ms": int((ended - started) * 1000),
            "generation_tok_s": tok_s,
            "response": content.strip()[:80],
            "thinking_response": thinking.strip()[:80],
        }
        MODELS.record_qualification(name, result)
        SUP.release(rid, "ok" if result["ok"] else "failed", "qualification complete")
        return result
    except InterruptedError as e:
        # The logical lease was already archived by preemption.
        return {"ok": False, "preempted": True, "error": str(e)}
    except Exception as e:
        SUP.release(rid, "error", str(e))
        result = {"ok": False, "tested_at": now(), "error": str(e)}
        MODELS.record_qualification(name, result)
        return result


def background_qualifier():
    """Use genuinely idle cycles; never cold-load a model and never outrank a person."""
    while True:
        time.sleep(5)
        if SUP.status()["active"] is not None:
            continue
        if now() - SUP.last_human_activity < QUALIFY_IDLE_SECONDS:
            continue
        profiles = load_profiles()
        for m in MODELS.discover(force=True):
            if not m.get("resident"):
                continue
            q = (profiles.get(m["name"]) or {}).get("qualification") or {}
            if now() - float(q.get("tested_at") or 0) < QUALIFY_RECHECK_SECONDS:
                continue
            qualify_model(m["name"], automatic=True)
            break


def pulse_loop():
    last_peer = 0.0
    while True:
        SUP.reconcile()
        MODELS.discover()
        if now() - last_peer >= PEER_REFRESH_SECONDS:
            PEERS.refresh()
            last_peer = now()
        # Align approximately to the next shared wall-clock beat without making work
        # wait for it. Events and jobs remain immediate.
        delay = PULSE_SECONDS - (now() % PULSE_SECONDS)
        time.sleep(max(.05, delay))


MANAGED_SERVICES = {
    "node": {"linux": "future-crash-look-node.service", "darwin": "com.futurecrash.look.node"},
    "signal": {"linux": "signal-window.service", "darwin": "com.futurecrash.signal-window"},
    "ollama": {"linux": "ollama.service", "darwin": None},
    "comfy": {"linux": "server-comfy.service", "darwin": None},
    "mercury": {"linux": "server-mercury.service", "darwin": None},
}

def service_status(name: str):
    """Inspect only named services. Fabric is deliberately not a remote shell."""
    spec = MANAGED_SERVICES.get(name)
    if not spec:
        return {"ok": False, "error": "unknown managed service", "service": name}
    system = platform.system().lower()
    unit = spec.get(system)
    if not unit:
        # Ollama on macOS is often app-managed; report reachability without pretending
        # launchd owns it.
        if name == "ollama":
            return {"ok": True, "service": name, "managed": False,
                    "state": "running" if probe("127.0.0.1",11434) else "stopped"}
        return {"ok": True, "service": name, "managed": False, "state": "unmanaged"}
    if system == "linux":
        p = run("systemctl", "--user", "is-active", unit, timeout=2)
        # Ollama is commonly a system unit, unlike our user services.
        if name == "ollama" and (not p or p.returncode):
            p = run("systemctl", "is-active", unit, timeout=2)
        state = (p.stdout.strip() if p and p.stdout.strip() else "inactive")
        return {"ok": True, "service": name, "managed": True, "unit": unit, "state": state}
    if system == "darwin":
        p = run("launchctl", "print", f"gui/{os.getuid()}/{unit}", timeout=2)
        return {"ok": True, "service": name, "managed": True, "unit": unit,
                "state": "running" if p and p.returncode == 0 else "stopped"}
    return {"ok": True, "service": name, "managed": False, "state": "unmanaged"}


def service_action(name: str, action: str, confirmed=False):
    if action not in {"start", "stop", "restart"}:
        return {"ok": False, "error": "unsupported service action"}
    if not confirmed:
        return {"ok": False, "confirmation_required": True,
                "message": f"{action} {name} requires explicit confirmation"}
    st = service_status(name)
    if not st.get("ok") or not st.get("managed"):
        return {**st, "ok": False, "error": st.get("error") or "service is not Fabric-managed on this platform"}
    system = platform.system().lower(); unit = st["unit"]
    if name == "node" and action in {"stop", "restart"}:
        return {"ok": False, "error": "self stop/restart is intentionally deferred; use the platform service manager locally"}
    if system == "linux":
        argv = ["systemctl", "--user", action, unit]
        p = run(*argv, timeout=12)
        if name == "ollama" and (not p or p.returncode):
            # Do not sudo or elevate remotely. A system-owned Ollama remains observable.
            return {"ok": False, "service": name, "error": "Ollama is system-managed; Fabric will not elevate privileges"}
    elif system == "darwin":
        domain=f"gui/{os.getuid()}/{unit}"
        verb={"start":"kickstart","restart":"kickstart","stop":"kill"}[action]
        argv=["launchctl",verb]
        if action == "restart": argv.append("-k")
        if action == "stop": argv.append("TERM")
        argv.append(domain)
        p=run(*argv,timeout=12)
    else:
        return {"ok": False, "error": "unsupported platform"}
    if not p or p.returncode:
        return {"ok": False, "service": name, "error": (p.stderr.strip() if p else "command failed")}
    return {"ok": True, "service": name, "action": action, "state": service_status(name).get("state")}


def managed_services():
    return {name: service_status(name) for name in MANAGED_SERVICES}


class API(BaseHTTPRequestHandler):
    server_version = "FCLNode/4.2.0"

    def log_message(self, *a):
        pass

    def sendj(self, code, obj):
        b = json.dumps(obj, separators=(",", ":"), ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def body(self):
        try:
            return json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))) or b"{}")
        except Exception:
            return {}

    def do_GET(self):
        path = urlparse(self.path).path
        if path in ("/health", "/v1/health"):
            return self.sendj(200, {"ok": True, "version": VERSION, "pulse": pulse_number()})
        if path in ("/node", "/v1/node", "/v1/status"):
            return self.sendj(200, node_info())
        if path == "/v1/advertisement":
            return self.sendj(200, advertisement())
        if path == "/v1/pulse":
            return self.sendj(200, {"epoch": "unix-1s-v1", "number": pulse_number(),
                                    "period_ms": int(PULSE_SECONDS*1000), "activity": SUP.status()})
        if path == "/v1/activity":
            return self.sendj(200, SUP.status())
        if path == "/v1/capabilities":
            return self.sendj(200, capabilities())
        if path == "/v1/models":
            return self.sendj(200, {"models": MODELS.discover()})
        if path == "/v1/services":
            return self.sendj(200, {"services": managed_services()})
        if path == "/v1/nodes":
            return self.sendj(200, {"self": node_info(), "peers": PEERS.public()})
        return self.sendj(404, {"error": "not found"})

    def do_POST(self):
        path = urlparse(self.path).path
        d = self.body()
        if path == "/v1/lease/acquire":
            lease, busy = SUP.acquire(str(d.get("owner") or "unknown"),
                                      str(d.get("priority") or "interactive"),
                                      str(d.get("phase") or "accepted"),
                                      str(d.get("detail") or ""),
                                      str(d.get("worker") or "local"))
            return self.sendj(200 if lease else 409, {"lease": lease, "busy": busy})
        if path == "/v1/lease/progress":
            ok = SUP.progress(str(d.get("id") or ""), d.get("phase"), d.get("detail"))
            return self.sendj(200 if ok else 404, {"ok": ok})
        if path == "/v1/lease/release":
            ok = SUP.release(str(d.get("id") or ""), str(d.get("status") or "ok"),
                             str(d.get("detail") or ""))
            return self.sendj(200 if ok else 404, {"ok": ok})
        if path == "/v1/models/qualify":
            name = str(d.get("model") or "")
            if not name:
                return self.sendj(400, {"error": "model required"})
            return self.sendj(200, qualify_model(name, automatic=False))
        if path == "/v1/services/action":
            name = str(d.get("service") or "")
            action = str(d.get("action") or "")
            result = service_action(name, action, bool(d.get("confirm")))
            code = 200 if result.get("ok") else (409 if result.get("confirmation_required") else 400)
            return self.sendj(code, result)
        return self.sendj(404, {"error": "not found"})


def _daemon_url(host: str, port: int, path: str) -> str:
    return f"http://{host}:{port}{path}"


def _daemon_get(host: str, port: int, path: str):
    try:
        return http_json(_daemon_url(host, port, path), timeout=2.5)
    except Exception as exc:
        raise RuntimeError(
            f"Unified Node is not reachable at {host}:{port}. "
            "Start/restart the Future Crash + LOOK node service."
        ) from exc


def _daemon_post(host: str, port: int, path: str, payload):
    try:
        return http_json(_daemon_url(host, port, path), payload, timeout=35.0)
    except Exception as exc:
        raise RuntimeError(f"Unified Node request failed at {host}:{port}: {exc}") from exc


def print_fabric_snapshot(snapshot):
    """Human view over the resident daemon's truth, never a throwaway CLI process."""
    local = snapshot.get("self") or {}
    pulse = (local.get("pulse") or {}).get("number", "?")
    name = local.get("name") or "local"
    print(f"FUTURE CRASH FABRIC · pulse {pulse} · node {name}")
    print("─" * 72)
    supervisor = local.get("supervisor") or {}
    active = supervisor.get("active")
    if active:
        print(f"local   {active.get('priority','?'):<11} {active.get('phase','?'):<14} "
              f"{active.get('owner','?')} · {active.get('state','?')}")
    else:
        print("local   idle")
    models = ((local.get("inference") or {}).get("models") or [])
    if models:
        print("models  " + ", ".join(
            str(m.get("name") or "?") + ("*" if m.get("resident") else "") for m in models
        ))
    for peer in snapshot.get("peers") or []:
        node = peer.get("node")
        if node:
            active = (node.get("supervisor") or {}).get("active")
            state = (active or {}).get("phase") or "idle"
            ppulse = (node.get("pulse") or {}).get("number", "?")
            print(f"peer    {peer.get('name','peer'):<18} {state:<14} pulse {ppulse}")
        else:
            # The normal Fabric view is about Future Crash nodes, not every phone on
            # the tailnet. Raw `nodes` JSON still exposes discovery diagnostics.
            continue


def _remote_url(snapshot, target, path):
    local=(snapshot.get("self") or {}).get("name")
    if target in {None, "", "local", local}:
        return _daemon_url(DEFAULT_HOST, DEFAULT_PORT, path)
    needle=str(target).lower()
    for peer in snapshot.get("peers") or []:
        names={str(peer.get("name") or "").lower(), str((peer.get("node") or {}).get("identity",{}).get("name") or "").lower()}
        if needle in names and peer.get("node") and peer.get("dns"):
            return f"https://{peer['dns']}:7332{path}"
    raise RuntimeError(f"Fabric node not found or not advertising: {target}")


def _target_get(host, port, target, path):
    snap=_daemon_get(host,port,"/v1/nodes")
    local=(snap.get("self") or {}).get("name")
    if target in {None,"","local",local}:
        return _daemon_get(host,port,path)
    url=_remote_url(snap,target,path)
    return http_json(url,timeout=4.0)


def _target_post(host, port, target, path, payload, timeout=45.0):
    snap=_daemon_get(host,port,"/v1/nodes")
    local=(snap.get("self") or {}).get("name")
    if target in {None,"","local",local}:
        return http_json(_daemon_url(host,port,path),payload,timeout=timeout)
    url=_remote_url(snap,target,path)
    return http_json(url,payload,timeout=timeout)


def _print_models(data, target="local"):
    print(f"FABRIC MODELS · {target}")
    print("─"*76)
    print(f"{'MODEL':<28} {'PARAM':>8}  V  T  R  {'STATE':<10} {'TOK/S':>7}")
    for m in data.get("models") or []:
        f=m.get("features") or {}; q=m.get("qualification") or {}
        state="resident" if m.get("resident") else "available"
        rate=q.get("generation_tok_s")
        print(f"{str(m.get('name') or '?'):<28.28} {str(m.get('parameter_size') or '?'):>8}  "
              f"{'✓' if f.get('vision') else '·'}  {'✓' if f.get('tools') else '·'}  {'✓' if f.get('thinking') else '·'}  "
              f"{state:<10} {str(rate if rate is not None else '—'):>7}")


def _watch(host,port,interval=1.0):
    try:
        while True:
            snap=_daemon_get(host,port,"/v1/nodes")
            print("\033[2J\033[H",end="")
            print_fabric_snapshot(snap)
            print("\nLIVE ACTIVITY")
            print("─"*72)
            rows=[("local",snap.get("self") or {})]
            rows += [(p.get("name","peer"),p.get("node") or {}) for p in snap.get("peers") or [] if p.get("node")]
            any_work=False
            for name,node in rows:
                sup=node.get("supervisor") or {}; active=sup.get("active")
                if active:
                    any_work=True
                    print(f"{name:<20} {active.get('priority','?'):<11} {active.get('phase','?'):<12} "
                          f"{active.get('owner','?'):<14} {active.get('state','?'):<8} idle {active.get('idle_ms',0)/1000:5.1f}s")
            if not any_work: print("all nodes idle")
            print("\nCtrl-C to leave Fabric watch",flush=True)
            time.sleep(interval)
    except KeyboardInterrupt:
        print()
        return 0


def main():
    ap=argparse.ArgumentParser(description="Future Crash + LOOK unified node")
    ap.add_argument("command",nargs="?",default="serve",
        choices=["serve","status","nodes","activity","pulse","fabric","watch","models","qualify","services","service"])
    ap.add_argument("args",nargs="*")
    ap.add_argument("--node",dest="node",default=None,help="target Fabric node name")
    ap.add_argument("--json",action="store_true",help="raw JSON where a human view exists")
    ap.add_argument("--yes",action="store_true",help="confirm a mutating managed-service action")
    ap.add_argument("--host",default=DEFAULT_HOST); ap.add_argument("--port",type=int,default=DEFAULT_PORT)
    ap.add_argument("--version",action="version",version=f"Future Crash + LOOK node {VERSION}")
    a=ap.parse_args()
    if a.command != "serve":
        try:
            if a.command=="watch": return _watch(a.host,a.port)
            if a.command=="fabric": print_fabric_snapshot(_daemon_get(a.host,a.port,"/v1/nodes")); return 0
            if a.command=="nodes": print(json.dumps(_daemon_get(a.host,a.port,"/v1/nodes"),indent=2)); return 0
            path={"status":"/v1/node","activity":"/v1/activity","pulse":"/v1/pulse","models":"/v1/models","services":"/v1/services"}.get(a.command)
            if path:
                data=_target_get(a.host,a.port,a.node,path)
                if a.command=="models" and not a.json: _print_models(data,a.node or "local")
                else: print(json.dumps(data,indent=2))
                return 0
            if a.command=="qualify":
                if not a.args: ap.error("qualify requires MODEL")
                print(json.dumps(_target_post(a.host,a.port,a.node,"/v1/models/qualify",{"model":a.args[0]},timeout=45),indent=2)); return 0
            if a.command=="service":
                if len(a.args)<2: ap.error("service requires SERVICE ACTION")
                service,action=a.args[:2]
                if not a.yes:
                    target=a.node or "local"
                    answer=input(f"{action} {service} on {target}? [y/N] ").strip().lower()
                    if answer not in {"y","yes"}: print("cancelled"); return 1
                print(json.dumps(_target_post(a.host,a.port,a.node,"/v1/services/action",{"service":service,"action":action,"confirm":True}),indent=2)); return 0
        except (RuntimeError, urllib.error.URLError, urllib.error.HTTPError) as exc:
            print(f"FCL NODE · {exc}",file=sys.stderr); return 1
    threading.Thread(target=pulse_loop,name="fabric-pulse",daemon=True).start()
    threading.Thread(target=background_qualifier,name="model-qualifier",daemon=True).start()
    srv=ThreadingHTTPServer((a.host,a.port),API)
    print(f"Future Crash + LOOK node {VERSION} · http://{a.host}:{a.port} · pulse {PULSE_SECONDS:g}s",flush=True)
    try: srv.serve_forever(poll_interval=.2)
    except KeyboardInterrupt: pass
    finally: srv.server_close()
    return 0


if __name__ == "__main__":
    main()
