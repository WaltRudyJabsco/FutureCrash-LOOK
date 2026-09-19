#!/usr/bin/env python3
"""Future Crash + LOOK Unified Node 4.3.

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

try:
    from .fabric_packet import ArtifactStore, FabricStore, normalize_packet, packet_summary, new_id
except ImportError:
    from fabric_packet import ArtifactStore, FabricStore, normalize_packet, packet_summary, new_id
from urllib.parse import urlparse, parse_qs

VERSION = "4.5.0"
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
FABRIC_DB = STATE / "fabric.sqlite3"
ARTIFACT_ROOT = STATE / "artifacts"
FABRIC_STORE = FabricStore(FABRIC_DB)
ARTIFACTS = ArtifactStore(ARTIFACT_ROOT)


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


def qualify_model(name: str, automatic=False, external_lease_id=None):
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
    owns_lease = external_lease_id is None
    if owns_lease:
        lease, busy = SUP.acquire(f"qualify:{name}", "background", "qualifying", "tiny model self-test")
        if not lease:
            return {"ok": False, "skipped": "supervisor busy", "busy": busy}
        rid = lease["id"]
    else:
        rid = str(external_lease_id)
        SUP.progress(rid, "qualifying", f"qualifying {name}")
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
        if owns_lease:
            SUP.release(rid, "ok" if result["ok"] else "failed", "qualification complete")
        return result
    except InterruptedError as e:
        # The logical lease may already have been archived by preemption.
        return {"ok": False, "preempted": True, "error": str(e)}
    except Exception as e:
        if owns_lease:
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


# ----- Fabric Work Packet execution -------------------------------------------------
# The packet is immutable. Queue/attempt/lease state is deliberately kept in the
# durable ledger and supervisor rather than written back into the packet.
JOB_WAKE = threading.Event()
MUTATING_OPERATIONS = {"service.start", "service.stop", "service.restart"}
OBSERVE_OPERATIONS = {
    "fabric.echo", "node.inspect", "node.rediscover", "model.list", "model.qualify", "model.infer",
    "service.list", "service.status",
} | MUTATING_OPERATIONS


def _requirements_ok(packet):
    req = (packet.get("capabilities") or {}).get("requires") or []
    if isinstance(req, dict):
        req = [k for k, v in req.items() if v]
    available = capabilities()
    models = MODELS.discover()
    model_features = {k: any((m.get("features") or {}).get(k) for m in models)
                      for k in ("text", "vision", "tools", "thinking", "embedding")}
    missing = []
    for item in req:
        name = str(item)
        if name in available and available.get(name):
            continue
        if name in model_features and model_features.get(name):
            continue
        missing.append(name)
    return (not missing), missing


def _job_authorized(packet, operation):
    authority = packet.get("authority") or {}
    grants = set(str(x) for x in (authority.get("grants") or []))
    confirmed = set(str(x) for x in (authority.get("confirmed_operations") or []))
    if operation in MUTATING_OPERATIONS:
        if operation not in confirmed:
            return False, f"{operation} requires explicit confirmation"
        if "service.control" not in grants and operation not in grants:
            return False, f"authority does not grant {operation}"
    elif operation == "model.qualify":
        if "model.qualify" not in grants and "model.infer" not in grants:
            return False, "authority does not grant model qualification"
    elif operation == "model.infer":
        if "model.infer" not in grants:
            return False, "authority does not grant model inference"
    elif operation not in OBSERVE_OPERATIONS:
        return False, f"unsupported Fabric operation: {operation}"
    return True, ""


def _dependencies_ready(packet):
    deps = (packet.get("relationships") or {}).get("dependencies") or []
    for dep in deps:
        dep_id = dep.get("id") if isinstance(dep, dict) else dep
        if not dep_id:
            continue
        job = FABRIC_STORE.get_job(str(dep_id))
        if not job or job.get("status") != "ok":
            return False
    return True


def _result_packet(task, data, *, worker, attempt):
    relationships = task.get("relationships") or {}
    root = relationships.get("root") or task.get("id")
    result = {
        "fabric": "fwp/1",
        "id": new_id("result"),
        "kind": "result",
        "created": now(),
        "origin": worker,
        "relationships": {
            "parent": task.get("id"),
            "root": root,
            "caused_by": task.get("id"),
            "dependencies": [],
        },
        "work": {
            "operation": (task.get("work") or {}).get("operation"),
            "objective": (task.get("work") or {}).get("objective"),
            "output": data,
        },
        "capabilities": {},
        "context": {},
        "execution": {"priority": (task.get("execution") or {}).get("priority", "interactive"), "cancellable": False},
        "authority": {"principal": "fabric", "grants": [], "confirmed_operations": []},
        "delivery": {"reply_to": (task.get("delivery") or {}).get("reply_to")},
        "provenance": {"node": worker, "software": f"future-crash-look/{VERSION}", "attempt": attempt},
        "extensions": {},
    }
    return normalize_packet(result, origin=worker)


def _acceptance_ok(packet, data):
    accept = (packet.get("work") or {}).get("acceptance") or {}
    required = accept.get("must_include") or []
    if not isinstance(data, dict):
        return (not required), ([] if not required else list(required))
    missing = [str(k) for k in required if str(k) not in data]
    return not missing, missing


def execute_packet(packet, job_id, attempt, worker, lease_id):
    operation = str((packet.get("work") or {}).get("operation") or "")
    inp = (packet.get("work") or {}).get("input") or {}
    if not isinstance(inp, dict):
        inp = {"value": inp}
    requirements_ok, missing = _requirements_ok(packet)
    if not requirements_ok:
        raise RuntimeError("missing required capabilities: " + ", ".join(missing))
    ok, reason = _job_authorized(packet, operation)
    if not ok:
        raise PermissionError(reason)
    if FABRIC_STORE.cancelled(job_id):
        raise InterruptedError("cancelled before execution")

    FABRIC_STORE.event(job_id, "progress", "dispatch", operation, node=worker)
    if operation == "fabric.echo":
        data = {"ok": True, "echo": inp, "node": worker}
    elif operation == "node.inspect":
        data = node_info()
    elif operation == "node.rediscover":
        MODELS.discover(force=True)
        PEERS.refresh()
        data = {"ok": True, "node": node_info()}
    elif operation == "model.list":
        data = {"models": MODELS.discover(force=True)}
    elif operation == "model.qualify":
        model = str(inp.get("model") or "")
        if not model:
            raise ValueError("model.qualify requires work.input.model")
        data = qualify_model(model, automatic=False, external_lease_id=lease_id)
        if not data.get("ok"):
            raise RuntimeError(data.get("error") or data.get("skipped") or "qualification failed")
    elif operation == "model.infer":
        model = str(inp.get("model") or "")
        models = MODELS.discover(force=True)
        if not model:
            eligible = [m for m in models if (m.get("features") or {}).get("text")]
            resident = [m for m in eligible if m.get("resident")]
            pool = resident or eligible
            if not pool:
                raise RuntimeError("no text model available")
            # Low-latency work prefers the smallest suitable model; otherwise prefer
            # the largest resident model. This is intentionally simple until real
            # qualification evidence is dense enough to drive routing.
            latency = str(((packet.get("capabilities") or {}).get("prefers") or {}).get("latency") or "")
            pool.sort(key=lambda m: int(m.get("size") or 0), reverse=(latency not in {"low","very-low"}))
            model = str(pool[0].get("name") or "")
        messages = inp.get("messages")
        if not isinstance(messages, list):
            messages = [{"role":"user","content":str(inp.get("prompt") or "")}]
        payload = {
            "model": model, "messages": messages, "stream": False,
            "keep_alive": inp.get("keep_alive", -1),
            "think": bool(inp.get("think", False)),
            "options": inp.get("options") if isinstance(inp.get("options"), dict) else {},
        }
        if isinstance(inp.get("tools"), list):
            payload["tools"] = inp["tools"]
        SUP.progress(lease_id, "inference", f"{model} responding")
        FABRIC_STORE.event(job_id, "progress", "inference", f"{model} responding", node=worker)
        req = urllib.request.Request("http://127.0.0.1:11434/api/chat",
                                     data=json.dumps(payload).encode(),
                                     headers={"Content-Type":"application/json"})
        timeout = max(5.0, min(300.0, float(inp.get("timeout") or 90)))
        with urllib.request.urlopen(req, timeout=timeout) as r:
            response = json.loads(r.read().decode("utf-8", "replace"))
        data = {"ok": True, "model": model, "message": response.get("message") or {},
                "done_reason": response.get("done_reason"),
                "prompt_eval_count": response.get("prompt_eval_count"),
                "eval_count": response.get("eval_count"),
                "eval_duration": response.get("eval_duration"),
                "total_duration": response.get("total_duration")}
    elif operation == "service.list":
        data = {"services": managed_services()}
    elif operation == "service.status":
        service = str(inp.get("service") or "")
        data = service_status(service)
    elif operation in MUTATING_OPERATIONS:
        service = str(inp.get("service") or "")
        action = operation.split(".", 1)[1]
        data = service_action(service, action, confirmed=True)
        if not data.get("ok"):
            raise RuntimeError(data.get("error") or "service action failed")
    else:
        raise ValueError(f"unsupported operation: {operation}")

    accepted, missing = _acceptance_ok(packet, data)
    if not accepted:
        raise ValueError("acceptance contract missing: " + ", ".join(missing))
    return data


def job_worker_loop():
    """Small deterministic worker. Distribution chooses a node before submission."""
    worker = identity()["name"]
    while True:
        JOB_WAKE.wait(timeout=.5)
        JOB_WAKE.clear()
        queued = [j for j in reversed(FABRIC_STORE.jobs(128)) if j.get("status") == "queued"]
        if not queued:
            continue
        # Human work first. FIFO within priority keeps behavior boring and inspectable.
        queued.sort(key=lambda j: (PRIORITY.get((j.get("packet") or {}).get("priority"), 9), j.get("accepted") or 0))
        for job in queued:
            packet = FABRIC_STORE.get_packet(job["id"])
            if not packet or not _dependencies_ready(packet):
                continue
            if FABRIC_STORE.cancelled(job["id"]):
                FABRIC_STORE.finish(job["id"], "cancelled", error="cancelled while queued", node=worker)
                continue
            priority = (packet.get("execution") or {}).get("priority", "interactive")
            operation = (packet.get("work") or {}).get("operation", "task")
            lease, busy = SUP.acquire(f"job:{job['id']}", priority, "dispatch", str(operation), worker=worker)
            if not lease:
                # Let the pulse/next wake try again; never spin against active human work.
                JOB_WAKE.set()
                break
            lease_id = lease["id"]
            attempt = FABRIC_STORE.start(job["id"], worker)
            SUP.progress(lease_id, "working", str(operation))
            FABRIC_STORE.event(job["id"], "progress", "working", str(operation), node=worker)
            try:
                budget = (packet.get("execution") or {}).get("budget") or {}
                wall_ms = int(budget.get("wall_ms") or 0)
                deadline = (packet.get("execution") or {}).get("deadline")
                if deadline and now() > float(deadline):
                    raise TimeoutError("job deadline already passed")
                started = now()
                data = execute_packet(packet, job["id"], attempt, worker, lease_id)
                if wall_ms and (now() - started) * 1000 > wall_ms:
                    raise TimeoutError("job exceeded wall_ms budget")
                result = _result_packet(packet, data, worker=worker, attempt=attempt)
                FABRIC_STORE.finish(job["id"], "ok", result=result, node=worker)
                SUP.release(lease_id, "ok", "packet complete")
            except InterruptedError as exc:
                FABRIC_STORE.finish(job["id"], "cancelled", error=str(exc), node=worker)
                SUP.release(lease_id, "cancelled", str(exc))
            except PermissionError as exc:
                FABRIC_STORE.finish(job["id"], "denied", error=str(exc), node=worker)
                SUP.release(lease_id, "denied", str(exc))
            except Exception as exc:
                FABRIC_STORE.finish(job["id"], "failed", error=str(exc), node=worker)
                SUP.release(lease_id, "failed", str(exc))
            break


class API(BaseHTTPRequestHandler):
    server_version = "FCLNode/4.5.0"

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
        if path == "/v1/jobs":
            return self.sendj(200, {"jobs": FABRIC_STORE.jobs()})
        if path.startswith("/v1/jobs/"):
            pid = path.split("/", 3)[3]
            job = FABRIC_STORE.get_job(pid)
            if not job:
                return self.sendj(404, {"error": "job not found"})
            job["packet_full"] = FABRIC_STORE.get_packet(pid)
            return self.sendj(200, job)
        if path == "/v1/events":
            q = parse_qs(urlparse(self.path).query)
            try: since = int((q.get("since") or [0])[0])
            except Exception: since = 0
            return self.sendj(200, {"events": FABRIC_STORE.events(since=since)})
        if path.startswith("/v1/artifacts/"):
            digest = path.split("/", 3)[3]
            try:
                meta, data = ARTIFACTS.get(digest)
            except Exception:
                return self.sendj(404, {"error": "artifact not found"})
            self.send_response(200)
            self.send_header("Content-Type", meta.get("media_type") or "application/octet-stream")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("X-Fabric-Digest", digest)
            self.end_headers()
            self.wfile.write(data)
            return
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
            if lease:
                FABRIC_STORE.event(lease["id"], "lease", lease.get("phase"), lease.get("detail"),
                                   node=identity()["name"], data={"owner": lease.get("owner"), "priority": lease.get("priority")})
            return self.sendj(200 if lease else 409, {"lease": lease, "busy": busy})
        if path == "/v1/lease/progress":
            rid = str(d.get("id") or "")
            ok = SUP.progress(rid, d.get("phase"), d.get("detail"))
            if ok:
                FABRIC_STORE.event(rid, "progress", d.get("phase"), d.get("detail"), node=identity()["name"])
            return self.sendj(200 if ok else 404, {"ok": ok})
        if path == "/v1/lease/release":
            rid = str(d.get("id") or "")
            status = str(d.get("status") or "ok")
            detail = str(d.get("detail") or "")
            ok = SUP.release(rid, status, detail)
            if ok:
                FABRIC_STORE.event(rid, "release", status, detail, node=identity()["name"])
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
        if path == "/v1/jobs":
            raw = d.get("packet") if isinstance(d.get("packet"), dict) else d
            try:
                packet = normalize_packet(raw, origin=identity()["name"])
                target = str((packet.get("delivery") or {}).get("target") or "")
                local = identity()["name"]
                if target and target not in {"local", local}:
                    snap = {"self": node_info(), "peers": PEERS.public()}
                    url = _remote_url(snap, target, "/v1/jobs")
                    result = http_json(url, {"packet": packet}, timeout=5.0)
                    result["forwarded_by"] = local
                    return self.sendj(202, result)
                job, created = FABRIC_STORE.submit(packet, node=local)
                if created:
                    JOB_WAKE.set()
                return self.sendj(202 if created else 200, {"ok": True, "created": created, "job": job})
            except ValueError as exc:
                return self.sendj(400, {"ok": False, "error": str(exc)})
            except Exception as exc:
                return self.sendj(502, {"ok": False, "error": str(exc)})
        if path.startswith("/v1/jobs/") and path.endswith("/control"):
            pid = path.split("/")[3]
            op = str(d.get("operation") or "")
            if op != "cancel":
                return self.sendj(400, {"error": "only cancel control is implemented in fwp/1"})
            ok = FABRIC_STORE.request_cancel(pid, node=identity()["name"], reason=str(d.get("reason") or "user"))
            active = SUP.status().get("active")
            if ok and active and active.get("owner") == f"job:{pid}":
                # The executor checks the durable flag; the supervisor flag makes
                # cooperative operations such as qualification notice immediately.
                with SUP.lock:
                    if SUP.active and SUP.active.id == active.get("id"):
                        SUP.active.cancel_requested = True
            JOB_WAKE.set()
            return self.sendj(200 if ok else 404, {"ok": ok})
        if path == "/v1/artifacts":
            try:
                encoded = str(d.get("base64") or "")
                meta = ARTIFACTS.put_base64(encoded, media_type=str(d.get("media_type") or "application/octet-stream"),
                                            name=(str(d.get("name")) if d.get("name") else None))
                return self.sendj(201, {"ok": True, "artifact": meta})
            except Exception as exc:
                return self.sendj(400, {"ok": False, "error": str(exc)})
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
    cursors = {}
    live_events = []
    try:
        while True:
            snap=_daemon_get(host,port,"/v1/nodes")
            sources=[("local",_daemon_url(host,port,""))]
            for peer in snap.get("peers") or []:
                if peer.get("node") and peer.get("dns"):
                    sources.append((peer.get("name") or "peer",f"https://{peer['dns']}:7332"))
            for name,base in sources:
                try:
                    data=http_json(f"{base}/v1/events?since={cursors.get(name,0)}",timeout=.8)
                    events=data.get("events") or []
                    if events:
                        cursors[name]=max(int(e.get("seq") or 0) for e in events)
                        for e in events:
                            e=dict(e); e["source"]=name; live_events.append(e)
                except Exception:
                    pass
            live_events=sorted(live_events,key=lambda e:float(e.get("ts") or 0))[-14:]
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
            print("\nEVENT TAPE")
            print("─"*72)
            if not live_events:
                print("waiting for Fabric events…")
            for e in live_events[-10:]:
                stamp=time.strftime("%H:%M:%S",time.localtime(float(e.get("ts") or now())))
                src=str(e.get("source") or e.get("node") or "?")[:18]
                typ=str(e.get("type") or "event")[:10]
                phase=str(e.get("phase") or "")[:14]
                detail=str(e.get("detail") or "")[:34]
                print(f"{stamp} {src:<18} {typ:<10} {phase:<14} {detail}")
            print("\nCtrl-C to leave Fabric watch",flush=True)
            time.sleep(interval)
    except KeyboardInterrupt:
        print()
        return 0


def _coerce_cli_value(value):
    try:
        return json.loads(value)
    except Exception:
        return value


def _submit_cli_packet(host, port, target, args, confirmed=False):
    if not args:
        raise RuntimeError("submit requires OPERATION")
    operation = args[0]
    inp = {}
    objective = ""
    for token in args[1:]:
        if "=" in token:
            k, v = token.split("=", 1)
            inp[k] = _coerce_cli_value(v)
        elif not objective:
            objective = token
        else:
            objective += " " + token
    local = (_daemon_get(host, port, "/v1/node") or {}).get("name") or "local"
    grants = ["observe", "model.infer", "model.qualify"]
    confirmed_ops = []
    if operation.startswith("service."):
        grants.append("service.control")
        if confirmed:
            confirmed_ops.append(operation)
    packet = {
        "fabric": "fwp/1",
        "kind": "task",
        "origin": local,
        "work": {"operation": operation, "objective": objective or operation, "input": inp},
        "execution": {"priority": "interactive", "cancellable": True,
                      "budget": {"wall_ms": 60000, "child_jobs": 0, "depth": 0}},
        "authority": {"principal": "user", "grants": grants, "confirmed_operations": confirmed_ops},
        "delivery": {"target": target or "local"},
        "relationships": {}, "capabilities": {}, "context": {}, "provenance": {}, "extensions": {},
    }
    return http_json(_daemon_url(host, port, "/v1/jobs"), {"packet": packet}, timeout=6.0)


def _print_jobs(data, target="local"):
    print(f"FABRIC JOBS · {target}")
    print("─" * 86)
    print(f"{'ID':<36} {'STATUS':<10} {'OPERATION':<20} {'WORKER':<18}")
    for j in data.get("jobs") or []:
        p = j.get("packet") or {}
        print(f"{str(j.get('id') or '?'):<36.36} {str(j.get('status') or '?'):<10.10} "
              f"{str(p.get('operation') or '?'):<20.20} {str(j.get('worker') or '—'):<18.18}")


def main():
    ap=argparse.ArgumentParser(description="Future Crash + LOOK unified node")
    ap.add_argument("command",nargs="?",default="serve",
        choices=["serve","status","nodes","activity","pulse","fabric","watch","models","qualify","services","service",
                 "jobs","job","submit","packet","cancel","events"])
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
            if a.command=="jobs":
                data=_target_get(a.host,a.port,a.node,"/v1/jobs")
                if a.json: print(json.dumps(data,indent=2))
                else: _print_jobs(data,a.node or "local")
                return 0
            if a.command=="job":
                if not a.args: ap.error("job requires ID")
                print(json.dumps(_target_get(a.host,a.port,a.node,f"/v1/jobs/{a.args[0]}"),indent=2)); return 0
            if a.command=="events":
                print(json.dumps(_target_get(a.host,a.port,a.node,"/v1/events"),indent=2)); return 0
            if a.command=="submit":
                if not a.args: ap.error("submit requires OPERATION")
                confirmed = bool(a.yes)
                if a.args[0].startswith("service.") and not confirmed:
                    target=a.node or "local"
                    answer=input(f"Submit {a.args[0]} on {target}? [y/N] ").strip().lower()
                    if answer not in {"y","yes"}: print("cancelled"); return 1
                    confirmed = True
                print(json.dumps(_submit_cli_packet(a.host,a.port,a.node,a.args,confirmed=confirmed),indent=2)); return 0
            if a.command=="packet":
                if not a.args: ap.error("packet requires FILE or -")
                raw = json.loads(sys.stdin.read() if a.args[0] == "-" else Path(a.args[0]).read_text())
                packet = raw.get("packet") if isinstance(raw,dict) and isinstance(raw.get("packet"),dict) else raw
                if a.node:
                    packet = dict(packet); delivery=dict(packet.get("delivery") or {}); delivery["target"]=a.node; packet["delivery"]=delivery
                print(json.dumps(http_json(_daemon_url(a.host,a.port,"/v1/jobs"),{"packet":packet},timeout=6.0),indent=2)); return 0
            if a.command=="cancel":
                if not a.args: ap.error("cancel requires JOB_ID")
                print(json.dumps(_target_post(a.host,a.port,a.node,f"/v1/jobs/{a.args[0]}/control",{"operation":"cancel","reason":"user"}),indent=2)); return 0
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
    threading.Thread(target=job_worker_loop,name="fabric-jobs",daemon=True).start()
    JOB_WAKE.set()
    srv=ThreadingHTTPServer((a.host,a.port),API)
    print(f"Future Crash + LOOK node {VERSION} · http://{a.host}:{a.port} · pulse {PULSE_SECONDS:g}s",flush=True)
    try: srv.serve_forever(poll_interval=.2)
    except KeyboardInterrupt: pass
    finally: srv.server_close()
    return 0


if __name__ == "__main__":
    main()
