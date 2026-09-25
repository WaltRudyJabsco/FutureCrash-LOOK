#!/usr/bin/env python3
"""Future Crash + LOOK Unified Node 6.4.5.

A small distributed supervisor for trusted personal machines. Immediate events stay
asynchronous; a one-second fabric pulse reconciles presence, leases and stale work.
"""
from __future__ import annotations

import argparse
import base64
import errno
import sys
import faulthandler
import signal
import json
import mimetypes
import os
import platform
import random
import re
import select
import sqlite3
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
try:
    from .memory_store import FabricMemory
except ImportError:
    from memory_store import FabricMemory
try:
    from .ui_model import actions as ui_actions, build_ui_model
except ImportError:
    from ui_model import actions as ui_actions, build_ui_model
try:
    from .decision import OpenJevShadow, new_request as new_decision_request, provider_status as decision_provider_status, plan as decision_plan
except ImportError:
    from decision import OpenJevShadow, new_request as new_decision_request, provider_status as decision_provider_status, plan as decision_plan
from urllib.parse import urlparse, parse_qs
try:
    from .fabric_identity import FabricIdentity, join_pairing
except ImportError:
    from fabric_identity import FabricIdentity, join_pairing
try:
    from .endpoint_auth import EndpointAuth
except ImportError:
    from endpoint_auth import EndpointAuth

VERSION = "6.4.5"
RELEASE_NAME = "JOSHUA"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 7332
DEFAULT_INGRESS_PORT = 0
PULSE_SECONDS = 1.0
PEER_REFRESH_SECONDS = 30.0
PEER_NODE_REFRESH_SECONDS = 20.0
PEER_UNKNOWN_BACKOFF_SECONDS = 180.0
PEER_FAILURE_BACKOFF_MAX_SECONDS = 300.0
WATCH_PEER_REFRESH_SECONDS = 3.0
MODEL_REFRESH_SECONDS = 15.0
QUALIFY_RECHECK_SECONDS = 24 * 60 * 60
QUALIFY_IDLE_SECONDS = 20.0
CURATOR_INTERVAL_SECONDS = 10.0
CURATOR_IDLE_SECONDS = 30.0
CURATOR_CONTEXT = 4096
CURATOR_MAX_RESIDENT = 3
INTERACTIVE_STALE_SECONDS = 45.0
BACKGROUND_STALE_SECONDS = 12.0
HISTORY_LIMIT = 64
PRIORITY = {"interactive": 0, "followup": 1, "background": 2}

STATE = Path.home() / ".local/share/future-crash-look"
STATE.mkdir(parents=True, exist_ok=True)
MODEL_STATE = STATE / "model_profiles.json"
LOOK_BENCHMARK_STATE = Path.home() / ".local/share/look/ollama_benchmarks.json"
LOOK_MODEL_PREFS = Path.home() / ".local/share/look/ollama_models.json"
LOOK_MEDIA_LIBRARY = Path.home() / ".local/share/look/media_library.json"
LOOK_FILE_CATALOG = Path.home() / ".local/share/look/file_catalog.sqlite3"
CURATOR_STATE = STATE / "model_curator.json"
FABRIC_DB = STATE / "fabric.sqlite3"
ARTIFACT_ROOT = STATE / "artifacts"
FABRIC_IDENTITY = FabricIdentity()
ENDPOINT_AUTH = EndpointAuth()
FABRIC_STORE = FabricStore(FABRIC_DB)
ARTIFACTS = ArtifactStore(ARTIFACT_ROOT)
FABRIC_MEMORY = FabricMemory()
WORKER_HEALTH = {"alive": False, "last_loop": 0.0, "last_error": None, "errors": 0}
IDENTITY_LOCK = threading.RLock()
IDENTITY_CACHE = {"name": socket.gethostname(), "hostname": socket.gethostname(), "tailscale": {}, "node_id": "", "fingerprint": ""}
ADVERTISEMENT_LOCK = threading.RLock()
ADVERTISEMENT_CACHE = {}
BEACON_LOCK = threading.RLock()
MEDIA_LIBRARY_LOCK = threading.RLock()
MEDIA_CATALOG_LOCK = threading.RLock()
MEDIA_CATALOG_CACHE = {"at": 0.0, "data": None, "local_mtime_ns": -1}
CURATOR_LOCK = threading.RLock()
BENCHMARK_GUARD = {"until": 0.0, "reason": ""}
BENCHMARK_GUARD_LOCK = threading.RLock()
BEACON_SEEN = set()
BEACON_PATTERNS = {
    "rgb": ("red", "green", "blue", "white"),
    "pulse": ("white", "off", "white"),
    "demo": ("white", "off", "red", "green", "blue", "white", "off", "red", "off", "green", "off", "blue", "off", "white", "white", "off"),
    "christmas": ("red", "green", "red", "green", "white", "green", "red", "off"),
    "disco": ("blue", "red", "white", "green", "blue", "off", "red", "green", "white", "off"),
}



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
    headers={"Connection":"close","User-Agent":f"FCLNode/{VERSION}"}
    if body: headers["Content-Type"]="application/json"
    # Local calls stay local. Remote Fabric calls carry the credential minted at pairing.
    host=(urllib.parse.urlparse(url).hostname or "").casefold()
    if host not in {"127.0.0.1","localhost","::1"}:
        headers.update(FABRIC_IDENTITY.auth_headers_for_url(url))
    req = urllib.request.Request(url, data=body, headers=headers)
    context = FABRIC_IDENTITY.ssl_context_for_url(url) if url.lower().startswith("https://") else None
    kwargs={"timeout":timeout}
    if context is not None: kwargs["context"]=context
    with urllib.request.urlopen(req, **kwargs) as r:
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


def refresh_identity():
    """Refresh transport hints while keeping Fabric identity transport-independent."""
    ts = tailscale_self()
    hostname = socket.gethostname()
    name = ((ts.get("dns") or "").split(".", 1)[0] or ts.get("hostname") or hostname)
    value = {"name": name, "hostname": hostname, "tailscale": ts}
    try:
        value.update(FABRIC_IDENTITY.public(name=name, hostname=hostname))
        # Friendly name and hostname remain mutable labels; node_id is the stable identity.
        value["name"] = name
        value["hostname"] = hostname
        value["tailscale"] = ts
        transports=FABRIC_IDENTITY.local_transports()
        if transports: value["transports"]=transports
    except Exception as exc:
        value["identity_error"] = str(exc)[:240]
    with IDENTITY_LOCK:
        IDENTITY_CACHE.clear()
        IDENTITY_CACHE.update(value)
    return dict(value)


def identity():
    """Return the last completed identity snapshot without spawning tailscale."""
    with IDENTITY_LOCK:
        return dict(IDENTITY_CACHE)


def albert_urls():
    """Publish Albert surfaces without making the Albert server itself network-facing."""
    urls={"local":"http://127.0.0.1:7330"}
    ts=tailscale_self()
    dns=str(ts.get("dns") or "").strip()
    if dns and ts.get("online", True):
        urls["tailnet"]=f"https://{dns}:7330"
    return urls


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
        "tailcat": bool(FABRIC_IDENTITY.local_transports().get("tailcat")),
        "ollama": probe("127.0.0.1", 11434),
        "signal": probe("127.0.0.1", 7331),
        "albert": probe("127.0.0.1", 7330),
        "albert.urls": albert_urls() if probe("127.0.0.1", 7330) else {},
        "node": True,
        "comfyui": probe("127.0.0.1", 8188),
        "mercury": probe("127.0.0.1", 8888),
        # Artifact transport is a first-class capability. Media is only the first
        # visible consumer; the same range primitive serves large datasets/files.
        "artifact.read": True,
        "artifact.range": True,
        "artifact.stream": True,
        "artifact.catalog": True,
        "file.catalog": LOOK_FILE_CATALOG.exists(),
        # Web search is a capability, not an account. A node advertises it only
        # when its local SearXNG JSON edge is reachable. Fabric may route clients
        # here from machines that have no search service of their own.
        "web.search": probe("127.0.0.1", 8888),
        # Human clarification is a Fabric capability, not a terminal-only prompt.
        "decision.request": True,
        "decision.answer": True,
        "decision.shadow": True,
        "decision.choice": probe("127.0.0.1", 8791),
        "decision.openjev": probe("127.0.0.1", 8791),
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


def load_look_benchmarks():
    """Read LOOK's durable benchmark evidence without making it node-owned state."""
    try:
        data=json.loads(LOOK_BENCHMARK_STATE.read_text(encoding="utf-8"))
        return data if isinstance(data,dict) else {}
    except Exception:
        return {}


def load_curator_state():
    """Small durable policy record. Auto curation is opt-in on existing installs."""
    default={"mode":"observe","profile":"balanced","last_action":0.0,"last_reason":"","hold_deep_until":0.0}
    try:
        data=json.loads(CURATOR_STATE.read_text(encoding="utf-8"))
        if isinstance(data,dict): default.update(data)
    except Exception:
        pass
    if default.get("mode") not in {"observe","auto"}: default["mode"]="observe"
    if default.get("profile") not in {"reflex","balanced","deep"}: default["profile"]="balanced"
    return default


def save_curator_state(state):
    tmp=CURATOR_STATE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    os.chmod(tmp,0o600)
    tmp.replace(CURATOR_STATE)


def _model_bytes(model):
    """Use quantized file size as a conservative cold-placement estimate."""
    try: return max(0,int(model.get("size") or 0))
    except Exception: return 0


def _benchmark_role_evidence(model):
    """Purpose evidence, not an IQ score. Values are only routing hints."""
    b=model.get("benchmark") or {}
    q=model.get("qualification") or {}
    size=_model_bytes(model)
    gib=size/(1024**3) if size else 0.0
    ttft=float(b.get("ttft") if isinstance(b.get("ttft"),(int,float)) else (q.get("ttft_ms") or 0)/1000.0)
    rate=float(b.get("rate") if isinstance(b.get("rate"),(int,float)) else (q.get("generation_tok_s") or 0))
    reasoning=int(b.get("reasoning") or 0) if isinstance(b.get("reasoning"),(int,float)) else 0
    tools=int(b.get("tools") or 0) if isinstance(b.get("tools"),(int,float)) else 0
    agent=bool(b.get("agent")); exact=bool(b.get("exact") or q.get("instruction_ok"))
    fit=str(b.get("fit") or "").upper()
    # Tuple ordering intentionally preserves raw evidence instead of manufacturing
    # a universal number. Callers can compare candidates for one role only.
    reflex=(1 if exact else 0, 1 if ttft and ttft<=2.0 else 0, rate, -gib)
    general=(1 if fit in {"EXCELLENT","GOOD"} else 0, tools, 1 if agent else 0, reasoning, rate, -abs(gib-6.0))
    deep=(reasoning, 1 if agent else 0, tools, 1 if fit not in {"POOR","ERROR"} else 0, gib)
    return {"reflex":reflex,"balanced":general,"deep":deep,
            "raw":{"ttft":ttft or None,"rate":rate or None,"reasoning":reasoning,"tools":tools,
                   "agent":agent,"exact":exact,"fit":fit or None,"size_gib":round(gib,2)}}


def _gpu_budget(models):
    """Estimate model-placement budget while respecting non-Ollama GPU residents.

    NVIDIA can tell us total/used VRAM. Subtract current Ollama VRAM to expose the
    amount occupied by Comfy, desktop graphics, etc. macOS uses a conservative
    unified-memory budget because Metal shares memory with the OS.
    """
    ollama_vram=sum(float(m.get("resident_size") or 0) for m in models if m.get("resident"))
    smi=binary("nvidia-smi")
    if smi:
        p=run(smi,"--query-gpu=memory.total,memory.used","--format=csv,noheader,nounits",timeout=2)
        if p and p.returncode==0 and p.stdout.strip():
            try:
                total_mib,used_mib=[float(x.strip()) for x in p.stdout.splitlines()[0].split(",")[:2]]
                total=total_mib*1024**2; used=used_mib*1024**2
                external=max(0.0,used-ollama_vram)
                reserve=max(1024**3,total*0.05)
                budget=max(0.0,total-external-reserve)
                return {"kind":"vram","total":int(total),"used":int(used),"external":int(external),
                        "reserve":int(reserve),"model_budget":int(budget)}
            except Exception:
                pass
    if platform.system().lower()=="darwin":
        p=run("sysctl","-n","hw.memsize",timeout=2)
        try: total=int((p.stdout or "0").strip()) if p and p.returncode==0 else 0
        except Exception: total=0
        if total:
            reserve=max(6*1024**3,int(total*0.25))
            return {"kind":"unified","total":total,"used":None,"external":None,"reserve":reserve,
                    "model_budget":max(0,total-reserve)}
    # Unknown accelerator: placement may still work through CPU, but do not guess a
    # dense multi-model set from disk sizes alone.
    return {"kind":"unknown","total":None,"used":None,"external":None,"reserve":None,"model_budget":None}


def _curator_disabled_models():
    try:
        data=json.loads(LOOK_MODEL_PREFS.read_text(encoding="utf-8"))
        return {str(x) for x in (data.get("disabled") or []) if str(x).strip()}
    except Exception:
        return set()


def _curator_candidates(models):
    disabled=_curator_disabled_models()
    rows=[]
    for m in models:
        if str(m.get("name") or "") in disabled:
            continue
        if not (m.get("features") or {}).get("text",True):
            continue
        row=dict(m); row["role_evidence"]=_benchmark_role_evidence(m)
        rows.append(row)
    return rows


def curator_plan(profile="balanced", models=None):
    """Return a deterministic resident-set recommendation for this node."""
    profile=profile if profile in {"reflex","balanced","deep"} else "balanced"
    models=list(models if models is not None else MODELS.discover(force=True))
    disabled=sorted(_curator_disabled_models())
    candidates=_curator_candidates(models)
    budget=_gpu_budget(models)
    limit=budget.get("model_budget")
    current=[m["name"] for m in models if m.get("resident")]
    if not candidates:
        return {"ok":False,"profile":profile,"target":[],"current":current,"budget":budget,"reason":"no text models installed"}

    def fits(selected, candidate):
        if limit is None:
            return len(selected)==0
        wanted=sum(int(_model_bytes(x)*1.10) for x in [*selected,candidate])
        return wanted <= int(limit)

    def best(rows, role, reverse=True):
        return sorted(rows,key=lambda m:m["role_evidence"][role],reverse=reverse)[0] if rows else None

    # Size bands are deliberately broad. Benchmarks decide within a band; size only
    # expresses the operational role of small/medium/large resident workers.
    small=[m for m in candidates if _model_bytes(m) and _model_bytes(m)<=3*1024**3]
    medium=[m for m in candidates if 3*1024**3 < _model_bytes(m) <= 11*1024**3]
    large=[m for m in candidates if _model_bytes(m)>11*1024**3]
    selected=[]; reason=[]
    if profile=="deep":
        choice=best(candidates,"deep")
        if choice:
            selected=[choice]; reason.append("deep work reserves the strongest deep candidate")
            # Large deep workers run alone by policy: reclaim VRAM and avoid turning a
            # 27/30B worker into a partially CPU-offloaded imitation of itself.
            if _model_bytes(choice)<=0.55*(limit or 0):
                helper=best([m for m in small if m["name"]!=choice["name"]],"reflex")
                if helper and fits(selected,helper): selected.append(helper); reason.append("small reflex helper fits beside deep worker")
    elif profile=="reflex":
        choice=best(small or medium or candidates,"reflex")
        if choice: selected=[choice]; reason.append("reflex work prefers the smallest measured responsive worker")
    else:
        mid=best(medium,"balanced") or best(small,"balanced") or best(candidates,"balanced")
        if mid and fits([],mid): selected=[mid]
        elif mid and limit is None: selected=[mid]
        helper=best([m for m in small if not selected or m["name"]!=selected[0]["name"]],"reflex")
        if helper and fits(selected,helper) and len(selected)<CURATOR_MAX_RESIDENT:
            selected.append(helper)
        if not selected:
            # A machine with only a large model still gets a usable plan.
            choice=best(candidates,"balanced")
            if choice: selected=[choice]
        reason.append("balanced keeps a capable general worker plus a small reflex worker when the measured budget permits")

    target=[m["name"] for m in selected]
    return {"ok":True,"profile":profile,"target":target,"current":current,"budget":budget,
            "disabled":disabled,"eligible":[m["name"] for m in candidates],
            "reason":"; ".join(reason),
            "models":[{"name":m["name"],"size":_model_bytes(m),"resident":bool(m.get("resident")),
                       "roles":m["role_evidence"]["raw"]} for m in candidates]}


def _ollama_residency_action(model, keep):
    payload={"model":model,"prompt":"","stream":False,"keep_alive":(-1 if keep else 0)}
    if keep:
        payload["options"]={"num_ctx":CURATOR_CONTEXT}
    return http_json("http://127.0.0.1:11434/api/generate",payload,timeout=180 if keep else 30)


def curator_apply(profile="balanced", reason="manual"):
    """Converge local Ollama residency on the requested canonical set."""
    if SUP.status()["active"] is not None:
        return {"ok":False,"skipped":"supervisor busy","plan":curator_plan(profile)}
    plan=curator_plan(profile)
    if not plan.get("ok"): return plan
    target=list(plan.get("target") or []); current=list(plan.get("current") or [])
    unloaded=[]; loaded=[]; errors=[]
    # Reclaim first. Large-model requests must not inherit VRAM pressure from the
    # balanced resident set.
    for name in current:
        if name not in target:
            try: _ollama_residency_action(name,False); unloaded.append(name)
            except Exception as exc: errors.append(f"unload {name}: {exc}")
    for name in target:
        if name not in current:
            try: _ollama_residency_action(name,True); loaded.append(name)
            except Exception as exc: errors.append(f"load {name}: {exc}")
    MODELS.discover(force=True); refresh_advertisement()
    state=load_curator_state(); state.update(last_action=now(),last_reason=reason,profile=profile)
    save_curator_state(state)
    result={"ok":not errors,"profile":profile,"target":target,"loaded":loaded,"unloaded":unloaded,"errors":errors,
            "reason":plan.get("reason"),"budget":plan.get("budget")}
    try:
        FABRIC_STORE.event("curator","model","curation",f"{profile}: "+(", ".join(target) or "none"),
                           node=identity()["name"],data={"loaded":loaded,"unloaded":unloaded,"reason":reason})
    except Exception:
        pass
    return result


def curator_status():
    state=load_curator_state(); profile=state.get("profile","balanced")
    plan=curator_plan(profile)
    return {"state":state,"plan":plan}


def benchmark_guard_active():
    with BENCHMARK_GUARD_LOCK:
        return now() < float(BENCHMARK_GUARD.get("until") or 0)


def benchmark_guard_state():
    with BENCHMARK_GUARD_LOCK:
        active=benchmark_guard_active()
        return {"active":active,"until":float(BENCHMARK_GUARD.get("until") or 0),"reason":BENCHMARK_GUARD.get("reason") or ""}


def benchmark_guard_set(active, ttl=3600, reason="operator benchmark"):
    with BENCHMARK_GUARD_LOCK:
        BENCHMARK_GUARD["until"] = now()+max(30,min(int(ttl or 3600),7200)) if active else 0.0
        BENCHMARK_GUARD["reason"] = str(reason or "") if active else ""
    return benchmark_guard_state()


def background_curator():
    """Opt-in resident-set manager. Human work always outranks reshuffling."""
    while True:
        time.sleep(CURATOR_INTERVAL_SECONDS)
        state=load_curator_state()
        if benchmark_guard_active(): continue
        if state.get("mode")!="auto": continue
        if SUP.status()["active"] is not None: continue
        if now()-SUP.last_human_activity < CURATOR_IDLE_SECONDS: continue
        profile="deep" if now()<float(state.get("hold_deep_until") or 0) else "balanced"
        try:
            plan=curator_plan(profile)
            if plan.get("ok") and set(plan.get("target") or [])!=set(plan.get("current") or []):
                curator_apply(profile,reason="background policy")
        except Exception:
            pass


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

    def snapshot(self):
        """Return the last completed model snapshot without doing Ollama I/O.

        Interactive request paths must never synchronously walk /api/show across
        every installed model. The pulse thread owns discovery; request handlers
        consume its last known-good result.
        """
        with self.lock:
            return list(self.cached)

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
            benchmarks = load_look_benchmarks()
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
                    "benchmark": ((benchmarks.get(name) or {})
                                  if (benchmarks.get(name) or {}).get("scope") == "local" else None),
                })
            self.cached, self.cached_at = out, now()
            return out

    def snapshot(self):
        """Return the last complete model snapshot without waiting on discovery.

        Discovery can query Ollama once per installed model.  Fabric routing and
        /v1/nodes are latency-sensitive, so they must never block behind that
        refresh lock.  The registry replaces ``cached`` atomically after a full
        refresh; readers can safely use the previous complete snapshot.
        """
        return list(self.cached)

    def record_qualification(self, name, result):
        with self.lock:
            self.profiles.setdefault(name, {})["qualification"] = result
            save_profiles(self.profiles)
            self.cached_at = 0


MODELS = ModelRegistry()


def peer_rows():
    """Return transport candidates for trusted Fabric peers.

    Tailcat candidates come from the trust store learned during pairing. Tailscale
    remains a discovery/fallback source, but is no longer required for peer rows.
    """
    merged={}
    # Native Tailcat transport learned during pairing.
    for node_id,row in (FABRIC_IDENTITY.trusted(public=True).get("nodes") or {}).items():
        if not isinstance(row,dict): continue
        tc=((row.get("transports") or {}).get("tailcat") or {}) if isinstance(row.get("transports"),dict) else {}
        endpoints=[str(x).rstrip('/') for x in (tc.get("endpoints") or []) if str(x).startswith('https://')]
        name=str(row.get("name") or row.get("hostname") or node_id)
        key=name.casefold()
        merged[key]={"name":name,"dns":"","ips":[],"online":True,"node_id":node_id,
                     "tailcat_endpoints":endpoints,"tailcat_cert_sha256":tc.get("cert_sha256"),
                     "trusted":bool(row.get("authorized")),"transport":"tailcat" if endpoints else "trusted"}

    ts = binary("tailscale")
    if ts:
        p = run(ts, "status", "--json", timeout=2)
        if p and not p.returncode:
            try: d=json.loads(p.stdout)
            except Exception: d={}
            for peer in (d.get("Peer") or {}).values():
                dns=(peer.get("DNSName") or "").rstrip(".")
                ips=peer.get("TailscaleIPs") or []
                name=(dns.split(".",1)[0] if dns else "") or peer.get("HostName") or (ips[0] if ips else "peer")
                key=str(name).casefold()
                row=merged.get(key,{"name":name,"tailcat_endpoints":[],"trusted":False})
                row.update({"dns":dns,"ips":ips,"online":bool(peer.get("Online")),"tailscale":True})
                merged[key]=row
    return sorted(merged.values(), key=lambda x:(not x.get("online",True),str(x.get("name") or "").lower()))


class PeerRegistry:
    """Slow, bounded peer discovery. The pulse is not a network poll."""
    def __init__(self):
        self.lock = threading.RLock()
        self.rows = []
        self.last_refresh = 0.0
        self.state = {}

    def refresh(self):
        rows=peer_rows(); t=now(); enriched=[]
        for p in rows:
            key=p.get("node_id") or p.get("dns") or p.get("name")
            prior=dict(self.state.get(key) or {})
            q=dict(p); q["node"]=prior.get("node"); q["node_seen_at"]=prior.get("node_seen_at"); q["node_error"]=prior.get("error")
            next_due=float(prior.get("next_due") or 0)
            candidates=[]
            # Native direct TLS is preferred. Each endpoint is certificate-pinned
            # by FabricIdentity using material learned during pairing.
            for base in p.get("tailcat_endpoints") or []:
                candidates.append(("tailcat",str(base).rstrip('/')))
            if p.get("online") and p.get("dns"):
                candidates.append(("tailscale",f"https://{p['dns']}:7332"))
            if candidates and t >= next_due:
                last_exc=None; success=None
                for transport,base in candidates:
                    try:
                        ad=http_json(base+"/v1/advertisement",timeout=.75)
                        success=(transport,base,ad); break
                    except Exception as exc:
                        last_exc=exc
                if success:
                    transport,base,ad=success
                    q.update(node=ad,node_seen_at=t,node_error=None,url=base,active_transport=transport)
                    # A successfully contacted trusted peer may publish new transport
                    # metadata after an upgrade. Bind it to the already-known Fabric
                    # public identity so 6.0 pairings learn Tailcat without re-pairing.
                    ident=ad.get("identity") if isinstance(ad,dict) else None
                    if isinstance(ident,dict) and ident.get("node_id") in (FABRIC_IDENTITY.trusted().get("nodes") or {}) and ident.get("transports"):
                        try: FABRIC_IDENTITY.trust(ident,source="transport-refresh")
                        except Exception: pass
                    prior.update(node=ad,node_seen_at=t,error=None,failures=0,url=base,active_transport=transport,
                                 next_due=t+PEER_NODE_REFRESH_SECONDS+random.uniform(0,3.0))
                else:
                    failures=int(prior.get("failures") or 0)+1; known=bool(prior.get("node"))
                    base_delay=PEER_NODE_REFRESH_SECONDS if known else PEER_UNKNOWN_BACKOFF_SECONDS
                    backoff=min(PEER_FAILURE_BACKOFF_MAX_SECONDS,base_delay*(2**min(failures-1,3)))
                    err=str(last_exc or "no reachable transport")
                    prior.update(error=err,failures=failures,next_due=t+backoff+random.uniform(0,5.0))
                    q["node_error"]=err
                    if prior.get("url"): q["url"]=prior.get("url"); q["active_transport"]=prior.get("active_transport")
            elif prior.get("url"):
                q["url"]=prior.get("url"); q["active_transport"]=prior.get("active_transport")
            self.state[key]=prior; enriched.append(q)
        live_keys={p.get("node_id") or p.get("dns") or p.get("name") for p in rows}
        self.state={k:v for k,v in self.state.items() if k in live_keys}
        with self.lock: self.rows,self.last_refresh=enriched,t

    def public(self):
        with self.lock:
            return [dict(r) for r in self.rows]


PEERS = PeerRegistry()


def _node_preferred_model(models):
    path = Path.home() / ".local/share/look/ollama_model"
    try:
        preferred = path.read_text(encoding="utf-8").strip()
    except OSError:
        preferred = ""
    names = {str(m.get("name") or "") for m in models}
    return preferred if preferred in names else None


def _build_advertisement():
    """Build the complete routing advertisement off the HTTP request path."""
    ident = identity()
    models = MODELS.snapshot()
    worker_age = max(0.0, now() - float(WORKER_HEALTH.get("last_loop") or 0))
    worker_ok = bool(WORKER_HEALTH.get("alive")) and worker_age < 3.0
    database_ok = worker_ok and not bool(WORKER_HEALTH.get("last_error"))
    return {
        "protocol": 1,
        "version": VERSION,
        "release_name": RELEASE_NAME,
        "runtime": {"ok": database_ok and worker_ok,
                    "database": database_ok, "job_worker": worker_ok,
                    "job_worker_error": WORKER_HEALTH.get("last_error")},
        "pulse": {"epoch": "unix-1s-v1", "number": pulse_number(), "period_ms": int(PULSE_SECONDS*1000)},
        "identity": ident,
        "platform": {"system": platform.system().lower(), "architecture": platform.machine()},
        "capabilities": capabilities(),
        "inference": {
            "available": bool(models),
            "models": models,
            "resident": [m["name"] for m in models if m.get("resident")],
            "preferred_model": _node_preferred_model(models),
        },
        "supervisor": SUP.status(),
        "curation": load_curator_state(),
    }

def refresh_advertisement():
    ad = _build_advertisement()
    with ADVERTISEMENT_LOCK:
        ADVERTISEMENT_CACHE.clear()
        ADVERTISEMENT_CACHE.update(ad)
    return ad

def advertisement():
    """Return an atomic, already-built control-plane snapshot."""
    with ADVERTISEMENT_LOCK:
        if ADVERTISEMENT_CACHE:
            ad = dict(ADVERTISEMENT_CACHE)
            ad["pulse"] = {"epoch": "unix-1s-v1", "number": pulse_number(),
                           "period_ms": int(PULSE_SECONDS*1000)}
            return ad
    return refresh_advertisement()


def node_info():
    ad = advertisement()
    ident=ad["identity"]
    return {"name": ident["name"], "hostname": ident["hostname"],
            "node_id": ident.get("node_id"), "fingerprint": ident.get("fingerprint"),
            "version": VERSION, "release_name": RELEASE_NAME, "platform": ad["platform"]["system"],
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
        if benchmark_guard_active():
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
    # Pulse is a local reconciliation clock, not a network poll. Network identity
    # and peer advertisements refresh on a slower cadence with jitter/backoff.
    last_peer = 0.0
    refresh_identity()
    MODELS.discover()
    refresh_advertisement()
    while True:
        SUP.reconcile()
        MODELS.discover()
        refresh_advertisement()
        if now() - last_peer >= PEER_REFRESH_SECONDS:
            refresh_identity()
            refresh_advertisement()
            PEERS.refresh()
            last_peer = now() + random.uniform(0, 4.0)
        delay = PULSE_SECONDS - (now() % PULSE_SECONDS)
        time.sleep(max(.05, delay))


MANAGED_SERVICES = {
    "node": {"linux": "future-crash-look-node.service", "darwin": "com.futurecrash.look.node"},
    "signal": {"linux": "signal-window.service", "darwin": "com.futurecrash.signal-window"},
    "albert": {"linux": "albert.service", "darwin": "com.futurecrash.albert"},
    "ollama": {"linux": "ollama.service", "darwin": None},
    "comfy": {"linux": "server-comfy.service", "darwin": None},
    "mercury": {"linux": "server-mercury.service", "darwin": None},
    "openjev": {"linux": "future-crash-look-openjev.service", "darwin": None},
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
    """Small deterministic worker. Ledger faults degrade/retry; the thread stays alive."""
    worker = identity()["name"]
    WORKER_HEALTH.update(alive=True, last_loop=now(), last_error=None)
    while True:
        try:
            WORKER_HEALTH["last_loop"] = now()
            JOB_WAKE.wait(timeout=.5)
            JOB_WAKE.clear()
            if benchmark_guard_active():
                continue
            queued = [j for j in reversed(FABRIC_STORE.jobs(128)) if j.get("status") == "queued"]
            WORKER_HEALTH.update(alive=True, last_loop=now(), last_error=None)
            if not queued:
                continue
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
        except Exception as exc:
            WORKER_HEALTH["alive"] = True
            WORKER_HEALTH["last_loop"] = now()
            WORKER_HEALTH["last_error"] = str(exc)
            WORKER_HEALTH["errors"] = int(WORKER_HEALTH.get("errors") or 0) + 1
            time.sleep(1.0)


def _curator_prepare_packet(packet):
    """For auto mode, make room for genuinely deep work before taking the lease."""
    state=load_curator_state()
    if state.get("mode")!="auto": return None
    prefs=(packet.get("capabilities") or {}).get("prefers") or {}
    tier=str(prefs.get("work_class") or ((packet.get("extensions") or {}).get("futurecrash") or {}).get("work_class") or "balanced")
    if tier!="deep": return None
    state["hold_deep_until"]=now()+90.0
    state["profile"]="deep"
    save_curator_state(state)
    with CURATOR_LOCK:
        return curator_apply("deep",reason="deep interactive work")


def _stream_model_infer(handler, raw):
    """Execute one FWP model.infer attempt and stream Ollama JSONL to the caller.

    The HTTP connection is the cancellation boundary: if the interface goes away,
    closing the upstream Ollama response stops this attempt instead of leaving an
    orphan generation behind.
    """
    worker = identity()["name"]
    packet = normalize_packet(raw.get("packet") if isinstance(raw, dict) and isinstance(raw.get("packet"), dict) else raw,
                              origin=worker)
    operation = (packet.get("work") or {}).get("operation")
    if operation != "model.infer":
        raise ValueError("stream endpoint accepts only model.infer")
    target = str((packet.get("delivery") or {}).get("target") or "")
    if target and target not in {"local", worker}:
        raise ValueError("stream request must be sent directly to its selected worker")
    ok, reason = _job_authorized(packet, operation)
    if not ok:
        raise PermissionError(reason)
    req_ok, missing = _requirements_ok(packet)
    if not req_ok:
        raise ValueError("missing capabilities: " + ", ".join(missing))
    job, created = FABRIC_STORE.submit(packet, node=worker)
    if not created:
        raise ValueError("stream packet id already exists")
    priority = (packet.get("execution") or {}).get("priority", "interactive")
    try:
        _curator_prepare_packet(packet)
    except Exception:
        pass
    lease, busy = SUP.acquire(f"job:{job['id']}", priority, "inference", "streaming model inference", worker=worker)
    if not lease:
        raise RuntimeError("worker busy")
    lease_id = lease["id"]
    lease_done = False

    def _release(status, detail):
        nonlocal lease_done
        if lease_done:
            return False
        lease_done = True
        return SUP.release(lease_id, status, detail)

    try:
        attempt = FABRIC_STORE.start(job["id"], worker)
        inp = (packet.get("work") or {}).get("input") or {}
        model = str(inp.get("model") or "")
        # The pulse thread owns model discovery. Streaming inference consumes the
        # last completed snapshot so starting a user request cannot synchronously
        # walk Ollama metadata for every installed model.
        models = MODELS.snapshot()
        if not models:
            models = MODELS.discover(force=False)
        if not model:
            model = _node_preferred_model(models) or ""
        if not model or model not in {str(m.get("name") or "") for m in models}:
            _release("failed", "model unavailable")
            FABRIC_STORE.finish(job["id"], "failed", error=f"model unavailable: {model}", node=worker)
            raise ValueError(f"model unavailable: {model}")
        messages = inp.get("messages")
        if not isinstance(messages, list):
            messages = [{"role":"user","content":str(inp.get("prompt") or "")}]
        # Vision pixels travel as artifacts, never inside the immutable work packet.
        # Rehydrate only at the selected worker's Ollama edge.
        hydrated=[]
        for message in messages:
            if not isinstance(message,dict):
                hydrated.append(message); continue
            copy=dict(message)
            refs=copy.pop("image_artifacts",None)
            if refs:
                images=[]
                for digest in refs:
                    _meta,data=ARTIFACTS.get(str(digest))
                    images.append(base64.b64encode(data).decode("ascii"))
                copy["images"]=images
            hydrated.append(copy)
        messages=hydrated
        payload = {"model":model, "messages":messages, "stream":True,
                   "keep_alive":inp.get("keep_alive",-1),
                   "options":inp.get("options") if isinstance(inp.get("options"),dict) else {}}
        if "think" in inp: payload["think"] = bool(inp.get("think"))
        if isinstance(inp.get("tools"),list): payload["tools"] = inp["tools"]
        FABRIC_STORE.event(job["id"], "progress", "inference", f"{model} streaming", node=worker)
        SUP.progress(lease_id, "inference", f"{model} streaming")
        upstream = urllib.request.Request("http://127.0.0.1:11434/api/chat", data=json.dumps(payload).encode(),
                                          headers={"Content-Type":"application/json"})
        timeout=max(5.0,min(300.0,float(inp.get("timeout") or 180)))
        final={}; first=True; chunks=0; committed=False
        try:
            with urllib.request.urlopen(upstream, timeout=timeout) as r:
                handler.send_response(200)
                handler.send_header("Content-Type","application/x-ndjson")
                handler.send_header("Cache-Control","no-store")
                handler.send_header("X-Fabric-Job",job["id"])
                handler.send_header("X-Fabric-Node",worker)
                handler.end_headers()
                committed=True
                for line in r:
                    if FABRIC_STORE.cancelled(job["id"]): raise InterruptedError("cancelled")
                    if not line.strip(): continue
                    try:
                        event=json.loads(line)
                    except Exception as exc:
                        preview=line.decode("utf-8","replace").strip()[:160]
                        raise RuntimeError(f"Ollama returned a non-JSON stream frame: {preview!r}") from exc
                    chunks += 1
                    fragment=event.get("message") or {}
                    if first and (fragment.get("content") or fragment.get("thinking") or fragment.get("tool_calls")):
                        first=False
                        FABRIC_STORE.event(job["id"],"progress","first-token",model,node=worker)
                        SUP.progress(lease_id,"first-token",model)
                    elif chunks % 16 == 0:
                        FABRIC_STORE.event(job["id"],"progress","stream",f"{chunks} chunks",node=worker)
                        SUP.progress(lease_id,"stream",f"{chunks} chunks")
                    handler.wfile.write(line); handler.wfile.flush()
                    if event.get("done"): final=event
            if not final.get("done"):
                raise RuntimeError("Ollama stream ended without a final done frame")
            data={"ok":True,"model":model,"message":{"role":"assistant"},
                  "done_reason":final.get("done_reason"),"prompt_eval_count":final.get("prompt_eval_count"),
                  "eval_count":final.get("eval_count"),"eval_duration":final.get("eval_duration"),
                  "total_duration":final.get("total_duration")}
            result=_result_packet(packet,data,worker=worker,attempt=attempt)
            FABRIC_STORE.finish(job["id"],"ok",result=result,node=worker)
            _release("ok","stream complete")
        except (BrokenPipeError, ConnectionResetError, InterruptedError) as exc:
            FABRIC_STORE.request_cancel(job["id"],node=worker,reason="stream client disconnected")
            FABRIC_STORE.finish(job["id"],"cancelled",error=str(exc),node=worker)
            _release("cancelled","stream client disconnected")
        except Exception as exc:
            FABRIC_STORE.finish(job["id"],"failed",error=str(exc),node=worker)
            _release("failed",str(exc))
            if committed:
                # Once HTTP 200/NDJSON headers are on the wire we cannot legally send
                # a second HTTP response. Keep the stream framed as JSON so clients
                # receive an explicit Fabric error instead of an HTTP status line in
                # the NDJSON body (which previously surfaced as JSONDecodeError).
                try:
                    frame={"done":True,"_fabric_error":True,"error":str(exc),
                           "message":{"role":"assistant","content":""}}
                    handler.wfile.write((json.dumps(frame,separators=(",",":"))+"\n").encode())
                    handler.wfile.flush()
                except (BrokenPipeError, ConnectionResetError, OSError):
                    pass
                return
            raise
    finally:
        # Any failure between lease acquisition and the streaming try block must
        # release the lane too (artifact hydration/model discovery included).
        # Otherwise a one-off vision error can leave a permanent ghost BUSY worker.
        if not lease_done:
            _release("failed", "stream aborted before completion")


class HTTPMetrics:
    """Tiny in-memory HTTP pressure meter. No I/O on the request hot path."""
    def __init__(self, plane):
        self.plane = str(plane)
        self.lock = threading.RLock()
        self.accepted = 0
        self.active = {}
        self.completed = 0
        self.rejected = 0
        self.errors = 0
        self.last_error = None
        self.accept_errors = 0
        self.last_accept_error = None
        self.peak_active = 0
        self.by_endpoint = {}
        self.by_source = {}
        self.request_times = []
        self.next_id = 0

    def accepted_connection(self):
        with self.lock:
            self.accepted += 1

    def rejected_connection(self):
        with self.lock:
            self.rejected += 1

    def request_error(self, exc):
        with self.lock:
            self.errors += 1
            self.last_error = f"{type(exc).__name__}: {exc}"[:240]

    def accept_error(self, exc):
        with self.lock:
            self.accept_errors += 1
            self.last_accept_error = f"{type(exc).__name__}: {exc}"[:240]

    def start(self, method, path, source):
        with self.lock:
            self.next_id += 1
            rid = self.next_id
            key = f"{str(method).upper()} {path}"
            self.by_endpoint[key] = int(self.by_endpoint.get(key) or 0) + 1
            self.by_source[source] = int(self.by_source.get(source) or 0) + 1
            self.request_times.append(now())
            cutoff = now() - 60.0
            if len(self.request_times) > 4096:
                self.request_times = [t for t in self.request_times if t >= cutoff]
            self.active[rid] = {"method": str(method).upper(), "path": str(path),
                                "source": str(source), "started": now()}
            self.peak_active = max(self.peak_active, len(self.active))
            return rid

    def finish(self, rid):
        if rid is None:
            return
        with self.lock:
            if self.active.pop(rid, None) is not None:
                self.completed += 1

    def public(self):
        t = now()
        with self.lock:
            oldest = sorted((dict(v, age_ms=int(max(0.0, t-float(v.get("started") or t))*1000))
                             for v in self.active.values()),
                            key=lambda x: x["age_ms"], reverse=True)[:12]
            recent_requests = sum(1 for ts in self.request_times if ts >= t - 60.0)
            return {"plane": self.plane, "accepted": self.accepted,
                    "connections_accepted": self.accepted,
                    "requests_started": sum(self.by_endpoint.values()),
                    "connections_without_request": max(0, self.accepted - sum(self.by_endpoint.values()) - self.rejected),
                    "requests_last_60s": recent_requests,
                    "requests_per_sec_60s": round(recent_requests / 60.0, 3),
                    "active": len(self.active), "completed": self.completed,
                    "requests_completed": self.completed,
                    "rejected": self.rejected, "errors": self.errors,
                    "last_error": self.last_error,
                    "accept_errors": self.accept_errors,
                    "last_accept_error": self.last_accept_error,
                    "peak_active": self.peak_active,
                    "by_endpoint": dict(sorted(self.by_endpoint.items())),
                    "by_source": dict(sorted(self.by_source.items())),
                    "oldest_active": oldest}


HTTP_METRICS = {"local": HTTPMetrics("local"), "ingress": HTTPMetrics("ingress")}


class FabricHTTPServer(ThreadingHTTPServer):
    # Keep the local control plane deliberately boring. Every socket accepted by
    # the process has exactly one owner and exactly one shutdown path.
    request_queue_size = 128
    daemon_threads = True
    block_on_close = False
    allow_reuse_address = True

    def __init__(self, server_address, RequestHandlerClass, *, plane="local"):
        self.plane = str(plane)
        self.metrics = HTTP_METRICS.setdefault(self.plane, HTTPMetrics(self.plane))
        self.max_active_requests = 32 if self.plane == "ingress" else 64
        self._request_slots = threading.BoundedSemaphore(self.max_active_requests)
        self.loop_heartbeat = time.monotonic()
        self.last_accept_success = time.monotonic()
        self.accept_failure_streak = 0
        self.last_accept_exception = None
        super().__init__(server_address, RequestHandlerClass)

    def service_actions(self):
        self.loop_heartbeat = time.monotonic()

    def get_request(self):
        # A readable listening socket plus a failing accept() creates a hot spin:
        # select immediately wakes again while the kernel backlog keeps filling.
        # Record that condition and back off so the watchdog can fail the daemon
        # cleanly instead of leaving an alive-but-useless process.
        try:
            request, address = super().get_request()
        except OSError as exc:
            self.accept_failure_streak += 1
            self.last_accept_exception = exc
            self.metrics.accept_error(exc)
            time.sleep(0.05)
            raise
        self.accept_failure_streak = 0
        self.last_accept_exception = None
        self.last_accept_success = time.monotonic()
        return request, address

    def _dispose_request(self, request):
        try:
            self.shutdown_request(request)
        except Exception:
            try:
                request.close()
            except Exception:
                pass

    def process_request(self, request, client_address):
        self.metrics.accepted_connection()
        if not self._request_slots.acquire(blocking=False):
            self.metrics.rejected_connection()
            self._dispose_request(request)
            return
        try:
            thread = threading.Thread(
                target=self._owned_request,
                args=(request, client_address),
                name="fabric-http",
                daemon=True,
            )
            thread.start()
        except BaseException:
            self._request_slots.release()
            self._dispose_request(request)
            raise

    def _owned_request(self, request, client_address):
        # Do not rely on ThreadingMixIn's implicit lifecycle here. This is the
        # control-plane invariant: accepted socket -> handler -> shutdown, even
        # for parser failures, disconnects, exceptions and rejected work.
        try:
            self.finish_request(request, client_address)
        except BaseException:
            self.handle_error(request, client_address)
        finally:
            try:
                self._dispose_request(request)
            finally:
                self._request_slots.release()

    def handle_error(self, request, client_address):
        exc = sys.exc_info()[1]
        if exc is not None:
            self.metrics.request_error(exc)
        if isinstance(exc, (BrokenPipeError, ConnectionResetError, TimeoutError, OSError)):
            return
        return super().handle_error(request, client_address)


def _local_accept_watchdog(server):
    """Terminate an alive-but-unusable local HTTP server with evidence.

    The 4.7.3 failure was not a sleeping accept loop: accept() itself stopped
    succeeding, so serve_forever spun while the kernel queue filled. Watch both
    the loop heartbeat and consecutive accept failures.
    """
    stale_seconds = 8.0
    fatal_accept_streak = 8
    while True:
        time.sleep(1.0)
        loop_age = time.monotonic() - float(getattr(server, "loop_heartbeat", 0.0))
        streak = int(getattr(server, "accept_failure_streak", 0))
        if loop_age <= stale_seconds and streak < fatal_accept_streak:
            continue
        exc = getattr(server, "last_accept_exception", None)
        reason = (f"accept failed {streak} consecutive times ({exc})" if streak >= fatal_accept_streak
                  else f"accept loop stalled for {loop_age:.1f}s")
        print(f"FCL NODE · local HTTP unhealthy: {reason}; terminating for service-manager recovery",
              file=sys.stderr, flush=True)
        faulthandler.dump_traceback(file=sys.stderr, all_threads=True)
        os._exit(70)


def _beacon_record(payload: dict) -> dict:
    """Record one synchronized Fabric beacon locally, idempotently."""
    bid = str(payload.get("id") or "")
    if not bid:
        raise ValueError("beacon id required")
    pattern = str(payload.get("pattern") or "rgb")
    if pattern not in BEACON_PATTERNS:
        raise ValueError(f"unknown beacon pattern: {pattern}")
    start = int(payload.get("start_pulse") or 0)
    if start <= 0:
        raise ValueError("start_pulse required")
    with BEACON_LOCK:
        if bid in BEACON_SEEN:
            return {"ok": True, "duplicate": True, "received_pulse": pulse_number()}
        BEACON_SEEN.add(bid)
        if len(BEACON_SEEN) > 256:
            BEACON_SEEN.clear(); BEACON_SEEN.add(bid)
    repeat = bool(payload.get("repeat", False))
    expires_pulse = int(payload.get("expires_pulse") or 0)
    show_id = str(payload.get("show_id") or bid)
    stopped = bool(payload.get("stopped", False))
    data = {"id": bid, "show_id": show_id, "origin": str(payload.get("origin") or "unknown"),
            "start_pulse": start, "pattern": pattern,
            "sequence": list(BEACON_PATTERNS[pattern]), "received_pulse": pulse_number(),
            "repeat": repeat, "expires_pulse": expires_pulse, "stopped": stopped}
    phase = "stopped" if stopped else ("renewed" if payload.get("renew") else "scheduled")
    FABRIC_STORE.event(None, "beacon", phase, f"{pattern} at pulse {start}",
                       node=identity()["name"], data=data)
    return {"ok": True, **data}


def _beacon_broadcast(pattern: str = "rgb", lead_pulses: int = 3) -> dict:
    """Schedule one diagnostic visual against the shared wall-clock pulse."""
    if pattern not in BEACON_PATTERNS:
        raise ValueError(f"unknown beacon pattern: {pattern}")
    lead_pulses = max(2, min(int(lead_pulses), 10))
    local = identity()["name"]
    payload = {"id": uuid.uuid4().hex[:12], "origin": local, "pattern": pattern,
               "start_pulse": pulse_number() + lead_pulses}
    local_result = _beacon_record(payload)
    snapshot = {"self": node_info(), "peers": PEERS.public()}
    deliveries = [{"node": local, "ok": True, "received_pulse": local_result.get("received_pulse")}]
    for peer in snapshot.get("peers") or []:
        ad = peer.get("node") or {}
        name = ((ad.get("identity") or {}).get("name") or peer.get("name"))
        if not name:
            continue
        try:
            result = http_json(_remote_url(snapshot, name, "/v1/beacon"), payload, timeout=.8)
            deliveries.append({"node": name, "ok": bool(result.get("ok")),
                               "received_pulse": result.get("received_pulse")})
        except Exception as exc:
            deliveries.append({"node": name, "ok": False, "error": str(exc)})
    return {"ok": all(x.get("ok") for x in deliveries), "id": payload["id"],
            "pattern": pattern, "start_pulse": payload["start_pulse"],
            "delivery": deliveries, "delivered": sum(1 for x in deliveries if x.get("ok")),
            "expected": len(deliveries)}


def _active_beacon(events, pulse=None):
    """Return the color scheduled for the current shared pulse, if any.

    Repeating light shows are leases: renewals extend expires_pulse while keeping
    the original start pulse, so every renderer derives the same frame locally.
    """
    current = pulse_number() if pulse is None else int(pulse)
    stopped = set()
    stop_all = False
    for event in reversed(events or []):
        if event.get("type") != "beacon":
            continue
        data = event.get("data") or {}
        show_id = str(data.get("show_id") or data.get("id") or "")
        if data.get("stopped"):
            if show_id == "*": stop_all = True
            elif show_id: stopped.add(show_id)
            continue
        if stop_all or (show_id and show_id in stopped):
            continue
        try:
            start = int(data.get("start_pulse"))
        except Exception:
            continue
        expires = int(data.get("expires_pulse") or 0)
        if expires and current > expires:
            continue
        seq = tuple(data.get("sequence") or BEACON_PATTERNS.get(str(data.get("pattern") or ""), ()))
        if not seq:
            continue
        offset = current - start
        if offset < 0:
            continue
        if data.get("repeat"):
            offset %= len(seq)
        elif offset >= len(seq):
            continue
        return {"color": seq[offset], "pulse": current, "id": data.get("id"),
                "show_id": show_id, "origin": data.get("origin"), "pattern": data.get("pattern"),
                "repeat": bool(data.get("repeat")), "expires_pulse": expires}
    return None


def _lights_broadcast(pattern="demo", *, show_id=None, start_pulse=None, repeat=False,
                      lease_pulses=8, stopped=False):
    """Broadcast a synchronized light show; renderers derive frames from pulse."""
    if pattern not in BEACON_PATTERNS:
        raise ValueError(f"unknown light pattern: {pattern}")
    local = identity()["name"]
    show_id = str(show_id or uuid.uuid4().hex[:12])
    start_pulse = int(start_pulse or (pulse_number() + 3))
    payload = {
        "id": uuid.uuid4().hex[:12], "show_id": show_id, "origin": local,
        "pattern": pattern, "start_pulse": start_pulse, "repeat": bool(repeat),
        "expires_pulse": (pulse_number() + max(3, int(lease_pulses))) if repeat and not stopped else 0,
        "renew": bool(repeat), "stopped": bool(stopped),
    }
    local_result = _beacon_record(payload)
    snapshot = {"self": node_info(), "peers": PEERS.public()}
    deliveries = [{"node": local, "ok": True, "received_pulse": local_result.get("received_pulse")}]
    for peer in snapshot.get("peers") or []:
        ad = peer.get("node") or {}
        name = ((ad.get("identity") or {}).get("name") or peer.get("name"))
        if not name:
            continue
        try:
            result = http_json(_remote_url(snapshot, name, "/v1/beacon"), payload, timeout=.8)
            deliveries.append({"node": name, "ok": bool(result.get("ok")),
                               "received_pulse": result.get("received_pulse")})
        except Exception as exc:
            deliveries.append({"node": name, "ok": False, "error": str(exc)})
    return {"ok": all(x.get("ok") for x in deliveries), "show_id": show_id,
            "pattern": pattern, "start_pulse": start_pulse, "repeat": bool(repeat),
            "delivery": deliveries, "delivered": sum(1 for x in deliveries if x.get("ok")),
            "expected": len(deliveries)}


def _memory_sync() -> dict:
    """Explicit bounded peer merge of shared/persona memory."""
    snapshot = {"self": node_info(), "peers": PEERS.public()}
    combined = list(FABRIC_MEMORY.public(include_local=False).get("items") or [])
    pulled = pushed = failures = 0
    peers = snapshot.get("peers") or {}
    if isinstance(peers, dict):
        peer_names = list(peers.keys())
    else:
        peer_names = [str(x.get("name") or "") for x in peers if isinstance(x, dict) and x.get("name")]
    for name in peer_names:
        try:
            remote = http_json(_remote_url(snapshot, name, "/v1/memory"), timeout=.8)
            combined.extend(remote.get("items") or [])
            pulled += 1
        except Exception:
            failures += 1
    merged = FABRIC_MEMORY.merge(combined)
    union = FABRIC_MEMORY.public(include_local=False).get("items") or []
    for name in peer_names:
        try:
            http_json(_remote_url(snapshot, name, "/v1/memory"), {"action":"merge", "items": union}, timeout=.8)
            pushed += 1
        except Exception:
            failures += 1
    FABRIC_STORE.event(None, "memory", "sync", f"{len(union)} shared/persona memories",
                       node=identity()["name"], data={"pulled":pulled,"pushed":pushed,"failures":failures})
    return {"ok": True, "count": len(union), "pulled": pulled, "pushed": pushed, "failures": failures, "merge": merged}



def _local_file_catalog():
    """Publish catalog coverage, never the whole path database over the network."""
    node=identity()["name"]
    if not LOOK_FILE_CATALOG.exists():
        return {"schema":"fabric-file-catalog-v1","node":node,"roots":[],"count":0}
    try:
        db=sqlite3.connect(f"file:{LOOK_FILE_CATALOG}?mode=ro",uri=True,timeout=.25)
        roots=[{"root":r,"scanned":st,"count":c} for r,st,c in db.execute("SELECT root,scanned,count FROM roots ORDER BY root")]
        count=db.execute("SELECT COUNT(*) FROM files").fetchone()[0]; db.close()
        return {"schema":"fabric-file-catalog-v1","node":node,"roots":roots,"count":count}
    except (sqlite3.Error,OSError) as exc:
        return {"schema":"fabric-file-catalog-v1","node":node,"roots":[],"count":0,"error":str(exc)}


def _file_search_terms(query):
    return re.findall(r"[\w.+-]+",str(query or "").casefold())


def _local_file_search(query,limit=80):
    """Bounded local metadata + FTS5 search; file contents never cross the network."""
    if not LOOK_FILE_CATALOG.exists(): return {"schema":"fabric-file-search-v2","node":identity()["name"],"entries":[],"count":0}
    terms=_file_search_terms(query); weak={"where","was","that","thing","i","wrote","write","find","file","files","show","me","the","a","an","my","named","called","about","something","with","of","to","in","on","for","and","or","is","it"}
    type_ext={"pdf":".pdf","zip":".zip","python":".py","markdown":".md","text":".txt"}; ext=None; words=[]
    for t in terms:
        if t in type_ext: ext=type_ext[t]
        elif t in weak or t in {"today","yesterday","recent","recently","big","biggest","large","largest"}: pass
        else: words.append(t)
    try:
        db=sqlite3.connect(f"file:{LOOK_FILE_CATALOG}?mode=ro",uri=True,timeout=.5); db.execute("PRAGMA busy_timeout=500")
        node=identity()["name"]; merged={}
        # Content first. OR gives natural-language recall; BM25 promotes files matching several useful words.
        if words:
            fts=" OR ".join('"'+w.replace('"','')+'"' for w in words[:16])
            try:
                sql="SELECT f.path,fi.name,fi.ext,fi.bytes,fi.mtime,fi.root,bm25(content_fts),snippet(content_fts,1,'[',']',' … ',18),COALESCE(cs.digest,'') FROM content_fts f JOIN files fi ON fi.path=f.path LEFT JOIN content_state cs ON cs.path=fi.path WHERE content_fts MATCH ?"
                fparams=[fts]
                if ext: sql+=" AND fi.ext=?"; fparams.append(ext)
                sql+=" ORDER BY bm25(content_fts) LIMIT ?"; fparams.append(int(limit))
                for row in db.execute(sql,fparams):
                    item=dict(zip(("path","name","ext","bytes","mtime","root","rank","snippet","digest"),row),node=node,match="content"); merged[item["path"]]=item
            except sqlite3.OperationalError: pass
        where=[]; params=[]
        if ext: where.append("files.ext=?"); params.append(ext)
        current=now()
        if "today" in terms: where.append("files.mtime>=?"); params.append(current-86400)
        elif "yesterday" in terms: where.append("files.mtime>=?"); params.append(current-172800)
        elif "recent" in terms or "recently" in terms: where.append("files.mtime>=?"); params.append(current-14*86400)
        for word in words: where.append("(files.name LIKE ? OR files.path LIKE ?)"); params.extend((f"%{word}%",f"%{word}%"))
        metadata_intent=bool(ext or any(t in terms for t in ("today","yesterday","recent","recently","big","biggest","large","largest")))
        # A lexical query that normalizes to no useful terms is not a request for
        # the newest catalog rows. Empty predicates are valid only for explicit
        # metadata intents such as "recent" or "biggest".
        if not words and not metadata_intent:
            db.close()
            return {"schema":"fabric-file-search-v2","node":node,"query":query,"entries":[],"count":0}
        sql="SELECT files.path,files.name,files.ext,files.bytes,files.mtime,files.root,COALESCE(content_state.digest,'') FROM files LEFT JOIN content_state ON content_state.path=files.path"+(" WHERE "+" AND ".join(where) if where else "")
        sql+=(" ORDER BY files.bytes DESC" if any(t in terms for t in ("big","biggest","large","largest")) else " ORDER BY files.mtime DESC")+" LIMIT ?"; params.append(int(limit))
        for row in db.execute(sql,params):
            item=dict(zip(("path","name","ext","bytes","mtime","root","digest"),row),node=node)
            if item["path"] in merged: merged[item["path"]]["match"]="name+content"
            else: item["match"]="name"; merged[item["path"]]=item
        db.close()
        def score(x): return (0,float(x.get("rank") or 0),-float(x.get("mtime") or 0)) if "rank" in x else (1,0,-float(x.get("mtime") or 0))
        entries=sorted(merged.values(),key=score)[:int(limit)]
        return {"schema":"fabric-file-search-v2","node":node,"query":query,"entries":entries,"count":len(entries)}
    except (sqlite3.Error,OSError) as exc:
        return {"schema":"fabric-file-search-v2","node":identity()["name"],"query":query,"entries":[],"count":0,"error":str(exc)}


def _fabric_file_catalog():
    local=_local_file_catalog(); nodes=[{"node":local.get("node"),"count":local.get("count",0),"online":True}]; errors=[]
    snapshot={"self":node_info(),"peers":PEERS.public()}
    for peer in snapshot.get("peers") or []:
        ad=peer.get("node") or {}; name=((ad.get("identity") or {}).get("name") or peer.get("name"))
        if not name or not (peer.get("url") or peer.get("tailcat_endpoints") or peer.get("dns")) or not ad: continue
        try:
            remote=http_json(_remote_url(snapshot,name,"/v1/files/catalog"),timeout=1.0)
            nodes.append({"node":name,"count":int(remote.get("count") or 0),"online":True})
        except Exception as exc: errors.append({"node":name,"error":str(exc)})
    return {"schema":"fabric-file-catalog-v1","generated":now(),"nodes":nodes,"locations":sum(int(x.get("count") or 0) for x in nodes),"errors":errors}


def _fabric_file_search(query,limit=80):
    local=_local_file_search(query,limit); entries=list(local.get("entries") or []); errors=[]
    snapshot={"self":node_info(),"peers":PEERS.public()}; encoded=urllib.parse.quote(str(query or ""))
    for peer in snapshot.get("peers") or []:
        ad=peer.get("node") or {}; name=((ad.get("identity") or {}).get("name") or peer.get("name"))
        if not name or not (peer.get("url") or peer.get("tailcat_endpoints") or peer.get("dns")) or not ad: continue
        try:
            remote=http_json(_remote_url(snapshot,name,f"/v1/files/search?q={encoded}&limit={int(limit)}"),timeout=1.2)
            entries.extend(dict(x) for x in (remote.get("entries") or []) if isinstance(x,dict))
        except Exception as exc: errors.append({"node":name,"error":str(exc)})
    terms=_file_search_terms(query); key=(lambda x:int(x.get("bytes") or 0)) if any(t in terms for t in ("big","biggest","large","largest")) else (lambda x:float(x.get("mtime") or 0))
    # Content identity, not pathname, defines one logical Fabric object. Keep all
    # physical copies as locations so nothing on disk is deduplicated or mutated.
    grouped={}
    for raw in entries:
        row=dict(raw); digest=str(row.get("digest") or "").strip(); node=str(row.get("node") or "")
        identity_key=("sha:"+digest) if digest else ("loc:"+node+":"+str(row.get("path") or ""))
        grouped.setdefault(identity_key,[]).append(row)
    logical=[]
    for copies in grouped.values():
        copies.sort(key=lambda x:(-float(x.get("mtime") or 0),str(x.get("node") or ""),str(x.get("path") or "")))
        primary=dict(copies[0])
        primary["locations"]=[{k:r.get(k) for k in ("node","path","root","mtime","bytes") if r.get(k) not in (None,"")} for r in copies]
        primary["copies"]=len(copies)
        if primary.get("digest"): primary["object_id"]=primary["digest"]
        logical.append(primary)
    logical=sorted(logical,key=key,reverse=True)[:int(limit)]
    return {"schema":"fabric-file-search-v3","generated":now(),"query":query,"entries":logical,"count":len(logical),"locations":sum(int(x.get("copies") or 1) for x in logical),"errors":errors}



def _local_web_search(query, limit=8):
    """Search this node's self-hosted SearXNG edge; never forwards to a peer."""
    query=str(query or "").strip()
    limit=max(1,min(int(limit or 8),20))
    node=identity()["name"]
    if not query:
        return {"schema":"fabric-web-search-v1","node":node,"provider":"searxng","query":query,"results":[],"count":0,"error":"query required"}
    params=urllib.parse.urlencode({"q":query,"format":"json"})
    base=os.environ.get("FCL_SEARXNG_URL","http://127.0.0.1:8888").rstrip("/")
    request=urllib.request.Request(base+"/search?"+params,headers={
        "Accept":"application/json",
        "User-Agent":"Future-Crash-Fabric/6.4.5",
    })
    try:
        with urllib.request.urlopen(request,timeout=8) as response:
            data=json.loads(response.read(2*1024*1024) or b"{}")
        results=[]
        for item in (data.get("results") or [])[:limit]:
            if not isinstance(item,dict): continue
            results.append({"title":str(item.get("title") or "").strip(),
                            "url":str(item.get("url") or "").strip(),
                            "content":" ".join(str(item.get("content") or "").split())[:1600]})
        return {"schema":"fabric-web-search-v1","node":node,"provider":"searxng","query":query,"results":results,"count":len(results)}
    except Exception as exc:
        return {"schema":"fabric-web-search-v1","node":node,"provider":"searxng","query":query,"results":[],"count":0,"error":str(exc)}


def _fabric_web_search(query, limit=8):
    """Use the nearest available accountless search capability in the Fabric."""
    local=_local_web_search(query,limit)
    if not local.get("error"):
        return local
    snapshot={"self":node_info(),"peers":PEERS.public()}
    encoded=urllib.parse.quote(str(query or ""))
    errors=[{"node":local.get("node"),"error":local.get("error")}]
    for peer in snapshot.get("peers") or []:
        ad=peer.get("node") or {}; caps=ad.get("capabilities") or {}
        name=((ad.get("identity") or {}).get("name") or peer.get("name"))
        if not name or not (peer.get("url") or peer.get("tailcat_endpoints") or peer.get("dns")) or not caps.get("web.search"): continue
        try:
            remote=http_json(_remote_url(snapshot,name,f"/v1/web/search/local?q={encoded}&limit={int(limit)}"),timeout=9.0)
            if not remote.get("error"):
                remote["via"]="fabric"
                return remote
            errors.append({"node":name,"error":remote.get("error")})
        except Exception as exc:
            errors.append({"node":name,"error":str(exc)})
    return {"schema":"fabric-web-search-v1","query":query,"results":[],"count":0,"provider":"none","errors":errors,"error":"no reachable Fabric SearXNG provider"}

def _read_media_library():
    """Read LOOK's local media discovery index without importing the LOOK UI layer."""
    with MEDIA_LIBRARY_LOCK:
        try:
            data = json.loads(LOOK_MEDIA_LIBRARY.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            data = {}
    return data if isinstance(data, dict) else {}


def _write_media_library(data):
    LOOK_MEDIA_LIBRARY.parent.mkdir(parents=True, exist_ok=True)
    with MEDIA_LIBRARY_LOCK:
        tmp = LOOK_MEDIA_LIBRARY.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        try:
            os.chmod(tmp, 0o600)
        except OSError:
            pass
        tmp.replace(LOOK_MEDIA_LIBRARY)
    with MEDIA_CATALOG_LOCK:
        MEDIA_CATALOG_CACHE["at"] = 0.0
        MEDIA_CATALOG_CACHE["data"] = None
        MEDIA_CATALOG_CACHE["local_mtime_ns"] = -1


def _local_media_catalog():
    """Publish discovered media as catalog rows; bytes remain owned by their source node."""
    library = _read_media_library()
    node = identity()["name"]
    rows = []
    for raw in library.get("entries") or []:
        if not isinstance(raw, dict) or not raw.get("path"):
            continue
        row = dict(raw)
        row["node"] = node
        row["identified"] = bool(str(row.get("digest") or "").startswith("sha256:"))
        rows.append(row)
    return {
        "schema": "fabric-media-catalog-v1",
        "node": node,
        "roots": [str(x) for x in (library.get("roots") or [])],
        "updated": float(library.get("updated") or 0.0),
        "entries": rows,
        "count": len(rows),
        "identified": sum(1 for row in rows if row.get("identified")),
    }


def _local_media_entry(entry_id):
    """Return one scanned local media row by stable catalog id without hashing it."""
    entry_id=str(entry_id or "").strip()
    if not entry_id:
        raise ValueError("media entry id required")
    for row in (_read_media_library().get("entries") or []):
        if isinstance(row,dict) and str(row.get("id") or "") == entry_id:
            path=Path(str(row.get("path") or "")).expanduser()
            if not path.is_file():
                raise FileNotFoundError(str(path))
            return dict(row),path
    raise FileNotFoundError(entry_id)


def _identify_media_entry(entry_id):
    """Promote one already-scanned local path to content-addressed Fabric identity."""
    entry_id = str(entry_id or "").strip()
    if not entry_id:
        raise ValueError("media entry id required")
    library = _read_media_library()
    entries = library.get("entries") or []
    selected = None
    for row in entries:
        if isinstance(row, dict) and str(row.get("id") or "") == entry_id:
            selected = row
            break
    if selected is None:
        raise FileNotFoundError(entry_id)
    path = str(selected.get("path") or "")
    meta = ARTIFACTS.register_file(path, media_type=str(selected.get("media_type") or "") or None,
                                   name=str(selected.get("title") or Path(path).name))
    selected["digest"] = meta["digest"]
    selected["identified_at"] = now()
    library["updated"] = now()
    _write_media_library(library)
    row = dict(selected)
    row["node"] = identity()["name"]
    row["identified"] = True
    return {"ok": True, "entry": row, "artifact": _artifact_public_metadata(meta)}


def _fabric_media_catalog(force=False):
    """Union media discoveries from currently reachable trusted Fabric nodes."""
    try:
        local_mtime_ns = int(LOOK_MEDIA_LIBRARY.stat().st_mtime_ns)
    except OSError:
        local_mtime_ns = -1
    with MEDIA_CATALOG_LOCK:
        cached = MEDIA_CATALOG_CACHE.get("data")
        age = now() - float(MEDIA_CATALOG_CACHE.get("at") or 0.0)
        same_local = int(MEDIA_CATALOG_CACHE.get("local_mtime_ns") or -1) == local_mtime_ns
        if cached is not None and not force and age < 3.0 and same_local:
            return cached

    local = _local_media_catalog()
    entries = list(local.get("entries") or [])
    nodes = [{"node": local.get("node"), "count": local.get("count", 0),
              "identified": local.get("identified", 0), "online": True}]
    errors = []
    snapshot = {"self": node_info(), "peers": PEERS.public()}
    for peer in snapshot.get("peers") or []:
        ad = peer.get("node") or {}
        name = ((ad.get("identity") or {}).get("name") or peer.get("name"))
        if not name or not (peer.get("url") or peer.get("tailcat_endpoints") or peer.get("dns")) or not ad:
            continue
        try:
            remote = http_json(_remote_url(snapshot, name, "/v1/media/catalog"), timeout=1.0)
            remote_rows = [dict(row) for row in (remote.get("entries") or []) if isinstance(row, dict)]
            entries.extend(remote_rows)
            nodes.append({"node": name, "count": len(remote_rows),
                          "identified": sum(1 for row in remote_rows if row.get("digest")), "online": True})
        except Exception as exc:
            errors.append({"node": name, "error": str(exc)})

    result = {
        "schema": "fabric-media-catalog-v1",
        "generated": now(),
        "entries": entries,
        "nodes": nodes,
        "locations": len(entries),
        "identified_locations": sum(1 for row in entries if row.get("digest")),
        "errors": errors,
    }
    with MEDIA_CATALOG_LOCK:
        MEDIA_CATALOG_CACHE["at"] = now()
        MEDIA_CATALOG_CACHE["data"] = result
        MEDIA_CATALOG_CACHE["local_mtime_ns"] = local_mtime_ns
    return result



def _look_command():
    """Resolve LOOK from a daemon/service environment without shell startup files."""
    env = str(os.getenv("FCL_LOOK") or "").strip()
    candidates = [env, shutil.which("lk"), str(Path.home()/".local/bin/lk"), str(Path.home()/".local/share/look/lk")]
    for raw in candidates:
        if not raw:
            continue
        path = Path(raw).expanduser()
        if path.is_file() and os.access(path, os.X_OK):
            return str(path.resolve())
    return ""


def _local_media_state():
    """Read this node's LOOK-owned media session through the public CLI surface."""
    lk = _look_command()
    if not lk:
        return {"available": False, "active": False, "state": "unavailable", "queue": [], "node": identity()["name"], "error": "LOOK command unavailable"}
    try:
        cp = subprocess.run([lk, "media", "state"], capture_output=True, text=True, timeout=2.0, env={**os.environ, "NO_COLOR": "1"})
        if cp.returncode:
            raise RuntimeError((cp.stderr or cp.stdout or "media state failed").strip())
        data = json.loads((cp.stdout or "{}").strip() or "{}")
        if not isinstance(data, dict):
            raise ValueError("invalid media state")
        data["available"] = True
        data["node"] = identity()["name"]
        data["output_id"] = "default"
        return data
    except Exception as exc:
        return {"available": False, "active": False, "state": "unavailable", "queue": [], "node": identity()["name"], "output_id": "default", "error": str(exc)[:500]}



def _local_media_full_session():
    lk=_look_command()
    if not lk:
        raise RuntimeError("LOOK command unavailable")
    cp=subprocess.run([lk,"media","session-json"],capture_output=True,text=True,timeout=2.5,env={**os.environ,"NO_COLOR":"1"})
    if cp.returncode:
        raise RuntimeError((cp.stderr or cp.stdout or "media session export failed").strip())
    data=json.loads((cp.stdout or "{}").strip() or "{}")
    if not isinstance(data,dict):
        raise ValueError("invalid media session")
    return data



def _media_player_binary():
    """Resolve mpv from normal shells and sparse service environments."""
    found=shutil.which("mpv")
    if found:
        return found
    for candidate in (
        Path.home()/".linuxbrew/bin/mpv",
        Path("/home/linuxbrew/.linuxbrew/bin/mpv"),
        Path("/opt/homebrew/bin/mpv"),
        Path("/usr/local/bin/mpv"),
        Path("/usr/bin/mpv"),
    ):
        if candidate.is_file() and os.access(candidate,os.X_OK):
            return str(candidate)
    return ""

def _local_media_audio_path(index=None):
    """Resolve one queue item to bytes local to this node for browser playback."""
    session=_local_media_full_session()
    queue=session.get("queue") or []
    if not queue:
        raise FileNotFoundError("media queue is empty")
    if index is None:
        index=int(session.get("current_index") or 0)
    index=max(0,min(int(index),len(queue)-1))
    entry=queue[index]
    local_name=identity()["name"]
    candidates=[]
    path=str(entry.get("path") or "").strip()
    if path:
        candidates.append(Path(path).expanduser())
    for loc in entry.get("locations") or []:
        if not isinstance(loc,dict):
            continue
        if str(loc.get("node") or "") not in {"",local_name}:
            continue
        raw=str(loc.get("path") or "").strip()
        if raw:
            candidates.append(Path(raw).expanduser())
    for candidate in candidates:
        try:
            if candidate.is_file():
                return candidate.resolve(), (mimetypes.guess_type(candidate.name)[0] or str(entry.get("media_type") or "application/octet-stream"))
        except OSError:
            pass
    digest=str(entry.get("digest") or "").strip()
    if digest:
        meta,source=ARTIFACTS.path_for(digest)
        return source, str(meta.get("media_type") or entry.get("media_type") or mimetypes.guess_type(source.name)[0] or "application/octet-stream")
    raise FileNotFoundError("media bytes are not local to this playback node")

def _local_media_output():
    state = _local_media_state()
    player=_media_player_binary()
    # Output availability means this node can ACCEPT a media session. An empty
    # or not-yet-created local session is not a playback failure.
    look_cmd=_look_command()
    available=bool(player) and bool(look_cmd)
    reason="" if available else ("mpv missing" if not player else "LOOK command unavailable")
    return {
        "node": identity()["name"],
        "output_id": "default",
        "label": f"{identity()['name']} · default",
        "available": available,
        "active": bool(state.get("active")),
        "state": str(state.get("state") or "stopped"),
        "reason": reason,
        "player": "mpv" if player else "",
        "presentation": "native",
        "capabilities": ["media.playback", "media.queue", "media.control", "media.video"] if available else ["media.queue", "media.control"],
    }


def _local_media_route(operation, payload):
    """Execute one bounded media operation on this node only."""
    lk = _look_command()
    if not lk:
        raise RuntimeError("LOOK command unavailable")
    operation = str(operation or "").casefold()
    if operation in {"play", "prepare"}:
        query = " ".join(str(payload.get("query") or "").split()).strip()
        kind = str(payload.get("kind") or "").strip().casefold()
        artist = " ".join(str(payload.get("artist") or "").split()).strip()
        selection = str(payload.get("selection") or "").strip().casefold()
        match_mode = str(payload.get("match_mode") or "").strip().casefold()
        limit = payload.get("limit")
        if not query and not (kind or artist or selection):
            raise ValueError("media query or selector required")
        argv = [lk, "media", "prepare" if operation == "prepare" else "play"]
        if query: argv.append(query)
        if kind: argv.extend(["--kind",kind])
        if artist: argv.extend(["--artist",artist])
        if selection: argv.extend(["--selection",selection])
        if match_mode == "literal": argv.append("--exact")
        if limit not in (None, "", 0, "0"): argv.extend(["--limit",str(limit)])
        if bool(payload.get("shuffle")):
            argv.append("--shuffle")
    elif operation == "control":
        action = str(payload.get("action") or "").casefold()
        aliases = {"previous": "prev", "resume": "play"}
        action = aliases.get(action, action)
        if action == "jump":
            try:
                index = int(payload.get("index")) + 1
            except (TypeError, ValueError):
                raise ValueError("invalid queue index")
            argv = [lk, "media", "jump", str(index)]
        elif action in {"play", "pause", "toggle", "next", "prev", "stop"}:
            argv = [lk, "media", action]
        else:
            raise ValueError("invalid media control")
    elif operation == "adopt":
        session=payload.get("session")
        if not isinstance(session,dict) or not session.get("queue"):
            raise ValueError("media session required")
        argv=[lk,"media","adopt","-"]
    else:
        raise ValueError("invalid media operation")
    cp = subprocess.run(argv, input=(json.dumps(session) if operation=="adopt" else None), capture_output=True, text=True, timeout=90.0, env={**os.environ, "NO_COLOR": "1"})
    if cp.returncode:
        raise RuntimeError((cp.stderr or cp.stdout or f"media {operation} failed").strip()[:1000])
    if operation == "prepare":
        try:
            prepared=json.loads((cp.stdout or "{}").strip() or "{}")
        except json.JSONDecodeError as exc:
            raise RuntimeError("invalid prepared media session") from exc
        session=prepared.get("session") or {}
        if not session.get("queue"):
            raise RuntimeError(str(prepared.get("error") or "prepared media queue is empty"))
        return {"ok":True,"node":identity()["name"],"state":"prepared","active":False,
                "index":int(session.get("current_index") or 0),"queue":session.get("queue") or [],
                "count":len(session.get("queue") or [])}
    state = _local_media_state()
    state["ok"] = True
    state["message"] = (cp.stdout or "").strip()[-1000:]
    return state


def _fabric_media_outputs():
    """Discover one default playback endpoint per reachable Fabric node."""
    local = _local_media_output()
    outputs = [local]
    errors = []
    snapshot = {"self": node_info(), "peers": PEERS.public()}
    for peer in snapshot.get("peers") or []:
        ad = peer.get("node") or {}
        name = ((ad.get("identity") or {}).get("name") or peer.get("name"))
        if not name or not (peer.get("url") or peer.get("tailcat_endpoints") or peer.get("dns")) or not ad:
            continue
        try:
            remote = http_json(_remote_url(snapshot, name, "/v1/media/output"), timeout=.8)
            if isinstance(remote, dict):
                outputs.append(remote)
        except Exception as exc:
            errors.append({"node": name, "error": str(exc)})
    return {"schema": "fabric-media-outputs-v1", "generated": now(), "outputs": outputs, "count": len(outputs), "errors": errors}


def _fabric_media_state(target=None):
    target = str(target or "").strip()
    local_name = identity()["name"]
    if not target or target == local_name:
        return _local_media_state()
    snapshot = {"self": node_info(), "peers": PEERS.public()}
    return http_json(_remote_url(snapshot, target, "/v1/media/state"), timeout=1.4)


def _fabric_media_route(target, operation, payload):
    target = str(target or "").strip()
    local_name = identity()["name"]
    if not target or target == local_name:
        return _local_media_route(operation, payload)
    snapshot = {"self": node_info(), "peers": PEERS.public()}
    body = dict(payload or {})
    body["operation"] = operation
    return http_json(_remote_url(snapshot, target, "/v1/media/route"), body, timeout=50.0)


def _fabric_media_full_session(target=None):
    target=str(target or "").strip()
    local_name=identity()["name"]
    if not target or target==local_name:
        return _local_media_full_session()
    snapshot={"self":node_info(),"peers":PEERS.public()}
    return http_json(_remote_url(snapshot,target,"/v1/media/session-full"),timeout=2.0)


def _fabric_media_move(source,target,index=None):
    """Move a logical session while keeping media bytes on their source node.

    A queue exported by one node contains local filesystem paths. Those paths are
    meaningless on another Mac/Linux node. For a cross-node handoff we rewrite
    each queue entry to the source node's range-capable media endpoint; mpv then
    streams the same bytes over Fabric without copying the library first.
    """
    source=str(source or identity()["name"]).strip()
    target=str(target or "").strip()
    if not target:
        raise ValueError("target media node required")
    session=_fabric_media_full_session(source)
    queue=session.get("queue") or []
    if not queue:
        raise ValueError(f"no media session on {source}")
    if index is not None:
        session["current_index"]=max(0,min(int(index),len(queue)-1))
    if source==target and index is None:
        return _fabric_media_state(target)
    if source!=target:
        snapshot={"self":node_info(),"peers":PEERS.public()}
        streamed=[]
        for i,row in enumerate(queue):
            item=dict(row)
            item["source_path"]=str(item.get("path") or "")
            item["path"]=_remote_url(snapshot,source,"/v1/media/audio?index="+str(i))
            item["node"]=source
            streamed.append(item)
        session=dict(session); session["queue"]=streamed
        session["stream_source_node"]=source
    result=_fabric_media_route(target,"adopt",{"session":session})
    if not result.get("ok"):
        raise RuntimeError(str(result.get("error") or "target did not accept media session"))
    try:
        _fabric_media_route(source,"control",{"action":"stop"})
    except Exception:
        result["source_stop_warning"]=True
    result["moved_from"]=source
    result["moved_to"]=target
    return result

def _local_artifact_catalog():
    node = identity()["name"]
    rows = []
    for meta in ARTIFACTS.list_metadata():
        row = _artifact_public_metadata(meta)
        row["node"] = node
        rows.append(row)
    return {"schema": "fabric-artifact-catalog-v1", "node": node, "artifacts": rows, "count": len(rows)}


def _fabric_artifact_catalog():
    local = _local_artifact_catalog()
    by_digest = {}
    errors = []
    snapshot = {"self": node_info(), "peers": PEERS.public()}

    def add_rows(payload, fallback_node):
        for raw in payload.get("artifacts") or []:
            if not isinstance(raw, dict):
                continue
            row = dict(raw)
            digest = str(row.get("digest") or "")
            if not digest:
                continue
            node = str(row.get("node") or fallback_node)
            current = by_digest.setdefault(digest, {k: v for k, v in row.items() if k != "node"})
            locations = current.setdefault("locations", [])
            if node and node not in locations:
                locations.append(node)

    add_rows(local, str(local.get("node") or "local"))
    for peer in snapshot.get("peers") or []:
        ad = peer.get("node") or {}
        name = ((ad.get("identity") or {}).get("name") or peer.get("name"))
        if not name or not (peer.get("url") or peer.get("tailcat_endpoints") or peer.get("dns")) or not ad:
            continue
        try:
            add_rows(http_json(_remote_url(snapshot, name, "/v1/artifacts"), timeout=1.0), name)
        except Exception as exc:
            errors.append({"node": name, "error": str(exc)})
    artifacts = sorted(by_digest.values(), key=lambda row: (str(row.get("media_type") or ""), str(row.get("name") or "").casefold()))
    return {"schema": "fabric-artifact-catalog-v1", "artifacts": artifacts,
            "count": len(artifacts), "errors": errors, "generated": now()}


def _artifact_public_metadata(meta):
    """Return artifact facts safe to expose to peer/browser consumers."""
    visible = {k: v for k, v in dict(meta or {}).items() if k not in {"path", "mtime_ns"}}
    visible["range"] = True
    visible["stream"] = True
    return visible


def _parse_byte_range(value, size):
    """Parse one HTTP byte range as inclusive start/end offsets.

    Fabric deliberately supports one range at a time: it is enough for media seeking
    and keeps the transport edge boring. Multipart ranges can be added only if a real
    consumer proves they are needed.
    """
    size = max(0, int(size))
    if not value:
        return 0, max(-1, size - 1), False
    raw = str(value).strip()
    if not raw.startswith("bytes=") or "," in raw:
        raise ValueError("unsupported byte range")
    spec = raw[6:].strip()
    if "-" not in spec or size <= 0:
        raise ValueError("unsatisfiable byte range")
    left, right = spec.split("-", 1)
    if not left:
        try:
            suffix = int(right)
        except ValueError as exc:
            raise ValueError("invalid byte range") from exc
        if suffix <= 0:
            raise ValueError("invalid byte range")
        start = max(0, size - suffix)
        end = size - 1
    else:
        try:
            start = int(left)
            end = int(right) if right else size - 1
        except ValueError as exc:
            raise ValueError("invalid byte range") from exc
        if start < 0 or end < start or start >= size:
            raise ValueError("unsatisfiable byte range")
        end = min(end, size - 1)
    return start, end, True


def _artifact_target_url(host, port, target, digest):
    path = f"/v1/artifacts/{digest}"
    if target in {None, "", "local"}:
        return _daemon_url(host, port, path)
    snapshot = _daemon_get(host, port, "/v1/nodes")
    local = (snapshot.get("self") or {}).get("name")
    if target == local:
        return _daemon_url(host, port, path)
    return _remote_url(snapshot, target, path)


def _decision_apply(decision, selected, *, source="human"):
    """Apply only the already-authorized packet attached to a selected choice.

    A renderer never executes work. It merely resolves the decision; normal FWP
    authorization remains the final gate for any continuation packet.
    """
    choice=None
    for item in decision.get("choices") or []:
        if isinstance(item,dict) and str(item.get("value")) == str(selected):
            choice=item; break
    if not choice or not isinstance(choice.get("packet"),dict):
        return {"ok":True,"continued":False}
    packet=normalize_packet(choice["packet"],origin=identity()["name"])
    job,created=FABRIC_STORE.submit(packet,node=identity()["name"])
    if created: JOB_WAKE.set()
    FABRIC_STORE.event(decision.get("job_id"),"decision","continued",str(selected),node=identity()["name"],
                       data={"decision_id":decision.get("id"),"continuation_job":job.get("id") if job else None,"source":source})
    return {"ok":True,"continued":True,"created":created,"job":job}


def _decision_resolve(did, selected, *, source="human"):
    before=FABRIC_STORE.get_decision(did)
    if not before:
        raise KeyError(did)
    if before.get("status") != "pending":
        return {"decision":before,"continuation":{"ok":True,"continued":False,"already_resolved":True}}
    decision=FABRIC_STORE.resolve_decision(did,selected,source=source,node=identity()["name"])
    return {"decision":decision,"continuation":_decision_apply(decision,selected,source=source)}



def _local_endpoints_payload():
    data=ENDPOINT_AUTH.list()
    data["node"]=identity()["name"]
    return data


def _fabric_endpoints():
    """Aggregate browser endpoint state without centralizing endpoint secrets."""
    rows=[]; errors=[]
    local=_local_endpoints_payload(); rows.append(local)
    snapshot={"self":node_info(),"peers":PEERS.public()}
    for peer in snapshot.get("peers") or []:
        ad=peer.get("node") or {}; name=((ad.get("identity") or {}).get("name") or peer.get("name"))
        base=_peer_base(peer)
        if not name or not ad or not base: continue
        try:
            remote=http_json(base+"/v1/endpoints",timeout=1.5)
            remote["node"]=name; rows.append(remote)
        except Exception as exc:
            errors.append({"node":name,"error":str(exc)})
    return {"schema":"fabric-endpoints-v2","nodes":rows,"errors":errors}


def _endpoint_find_pending(code):
    code=str(code or "").strip(); matches=[]
    data=_fabric_endpoints()
    for node in data.get("nodes") or []:
        for row in node.get("pending") or []:
            if str(row.get("code") or "") == code:
                matches.append((str(node.get("node") or "local"),row))
    return matches,data


def _endpoint_allow_fabric(code, mode="once"):
    matches,data=_endpoint_find_pending(code)
    if not matches:
        raise ValueError("endpoint code not found or expired anywhere in the reachable Fabric")
    if len(matches)>1:
        raise ValueError("endpoint code is ambiguous across Fabric nodes; wait for one to expire and retry")
    node,row=matches[0]; local=identity()["name"]
    if node in {"local",local}:
        approved=ENDPOINT_AUTH.allow(code,mode)
    else:
        snapshot={"self":node_info(),"peers":PEERS.public()}
        # A peer may advertise both Tailcat and Tailscale. Endpoint approval is a
        # control operation, so a transient direct-transport failure must fall back
        # rather than strand a browser pairing request.
        peer=_peer_for_target(snapshot,node)
        last_exc=None; response=None
        for base in _peer_bases(peer):
            try:
                response=http_json(base+"/v1/endpoints/allow",{"code":str(code),"mode":str(mode)},timeout=3.0)
                break
            except Exception as exc:
                last_exc=exc
        if response is None: raise RuntimeError(f"endpoint approval transport failed: {last_exc}")
        approved=response.get("endpoint") or {}
    return {"node":node,"endpoint":approved,"errors":data.get("errors") or []}


def _endpoint_revoke_fabric(endpoint_id):
    wanted=str(endpoint_id or ""); data=_fabric_endpoints(); matches=[]
    for node in data.get("nodes") or []:
        for bucket in ("trusted","sessions"):
            for row in node.get(bucket) or []:
                if str(row.get("endpoint_id") or "") == wanted:
                    matches.append(str(node.get("node") or "local"))
    if not matches: return {"ok":False,"error":"endpoint not found anywhere in the reachable Fabric"}
    if len(matches)>1: return {"ok":False,"error":"endpoint id is ambiguous across Fabric nodes"}
    node=matches[0]; local=identity()["name"]
    if node in {"local",local}: ok=ENDPOINT_AUTH.revoke(wanted)
    else:
        snapshot={"self":node_info(),"peers":PEERS.public()}
        peer=_peer_for_target(snapshot,node); last_exc=None; response=None
        for base in _peer_bases(peer):
            try:
                response=http_json(base+"/v1/endpoints/revoke",{"endpoint_id":wanted},timeout=3.0); break
            except Exception as exc: last_exc=exc
        if response is None: raise RuntimeError(f"endpoint revoke transport failed: {last_exc}")
        ok=bool(response.get("ok"))
    return {"ok":ok,"node":node}

def _fabric_decisions():
    """Aggregate pending decision requests from reachable trusted Fabric nodes."""
    local_name=identity()["name"]
    rows=[]; errors=[]
    for item in FABRIC_STORE.decisions(pending_only=True,limit=64):
        row=dict(item); row["node"]=local_name; rows.append(row)
    snapshot={"self":node_info(),"peers":PEERS.public()}
    for peer in snapshot.get("peers") or []:
        ad=peer.get("node") or {}
        name=((ad.get("identity") or {}).get("name") or peer.get("name"))
        if not name or not (peer.get("url") or peer.get("tailcat_endpoints") or peer.get("dns")) or not ad:
            continue
        try:
            remote=http_json(_remote_url(snapshot,name,"/v1/decisions"),timeout=.8)
            for item in remote.get("decisions") or []:
                if isinstance(item,dict):
                    row=dict(item); row["node"]=name; rows.append(row)
        except Exception as exc:
            errors.append({"node":name,"error":str(exc)})
    rows.sort(key=lambda x:float(x.get("created") or 0),reverse=True)
    return {"schema":"fabric-decisions-v1","decisions":rows,"count":len(rows),"errors":errors}


def _decision_answer_fabric(node, did, selected, source="human"):
    local=identity()["name"]
    if node in {None,"","local",local}:
        return _decision_resolve(did,selected,source=source)
    snapshot={"self":node_info(),"peers":PEERS.public()}
    url=_remote_url(snapshot,node,"/v1/decisions/answer")
    return http_json(url,{"id":did,"selected":selected,"source":source},timeout=3.0)


def _decision_expiry_loop():
    """Deadlines are progress guarantees: a missed prompt never locks the Fabric."""
    while True:
        try:
            for decision in FABRIC_STORE.expire_decisions(node=identity()["name"]):
                selected=decision.get("selected")
                if selected and str((decision.get("policy") or {}).get("timeout_action")) == "continue":
                    _decision_apply(decision,selected,source="timeout")
        except Exception as exc:
            try: FABRIC_STORE.event(None,"decision","expiry-error",str(exc),node=identity()["name"])
            except Exception: pass
        time.sleep(.5)


def _openjev_shadow(state, question, candidates, *, profile="workspace", consequence="low", reversible=True):
    result=OpenJevShadow().try_choice(state=state,question=question,candidates=candidates)
    if result.get("ok"):
        result["policy"]=decision_plan(profile=profile,confidence=float(result.get("confidence") or 0.0),
            margin=float(result.get("margin") or 0.0),consequence=consequence,reversible=bool(reversible)).public()
    phase="judge" if result.get("ok") else "provider-down"
    try:
        FABRIC_STORE.event(None,"decision",phase,str(result.get("choice") or result.get("error") or "openjev"),node=identity()["name"],
            data={"provider":"openjev","choice":result.get("choice"),"probabilities":result.get("probabilities") or {},
                  "confidence":result.get("confidence"),"margin":result.get("margin"),"elapsed_ms":result.get("elapsed_ms"),
                  "url":result.get("url")})
    except Exception:
        pass
    return result


class API(BaseHTTPRequestHandler):
    server_version = "FCLNode/6.4.5"

    def setup(self):
        self._metric_request_id = None
        super().setup()

    def parse_request(self):
        ok = super().parse_request()
        if ok:
            source = self.headers.get("X-Forwarded-For") or self.headers.get("Tailscale-User-Login") or self.client_address[0]
            path = urlparse(self.path).path
            self._metric_request_id = self.server.metrics.start(self.command, path, str(source))
        return ok

    def finish(self):
        try:
            super().finish()
        finally:
            try:
                self.server.metrics.finish(self._metric_request_id)
            except Exception:
                pass

    def log_message(self, *a):
        pass

    def sendj(self, code, obj):
        b = json.dumps(obj, separators=(",", ":"), ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(b)

    def body(self):
        try:
            return json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))) or b"{}")
        except Exception:
            return {}

    def _authorized_ingress(self, path):
        # The loopback control plane is already protected by host boundaries.
        # Any remotely reachable ingress route must prove paired Fabric trust.
        if getattr(self.server, "plane", "local") == "local":
            return True
        if path in {"/health","/v1/health","/v1/identity","/v1/advertisement","/v1/identity/pair"}:
            return True
        node_id=str(self.headers.get("X-Fabric-Node") or "")
        auth=str(self.headers.get("Authorization") or "")
        token=auth[7:].strip() if auth.startswith("Bearer ") else ""
        if FABRIC_IDENTITY.verify_peer(node_id,token):
            return True
        self.sendj(401,{"ok":False,"error":"unpaired or unauthorized Fabric peer","pair":"lk fabric pair-code"})
        return False

    def _serve_artifact(self, digest, *, head=False):
        try:
            meta, source = ARTIFACTS.path_for(digest)
        except Exception:
            if head:
                self.send_response(404)
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            return self.sendj(404, {"error": "artifact not found"})
        size = int(meta.get("bytes") or 0)
        try:
            start, end, partial = _parse_byte_range(self.headers.get("Range"), size)
        except ValueError:
            self.send_response(416)
            self.send_header("Content-Range", f"bytes */{size}")
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        length = 0 if size == 0 else (end - start + 1)
        self.send_response(206 if partial else 200)
        self.send_header("Content-Type", meta.get("media_type") or "application/octet-stream")
        self.send_header("Content-Length", str(length))
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("X-Fabric-Digest", digest)
        if partial:
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.end_headers()
        if head or length <= 0:
            return
        with source.open("rb") as fh:
            fh.seek(start)
            remaining = length
            while remaining > 0:
                chunk = fh.read(min(1024 * 1024, remaining))
                if not chunk:
                    break
                self.wfile.write(chunk)
                remaining -= len(chunk)

    def _serve_file_range(self, source, media_type="application/octet-stream", *, head=False):
        source=Path(source)
        size=source.stat().st_size
        try:
            start,end,partial=_parse_byte_range(self.headers.get("Range"),size)
        except ValueError:
            self.send_response(416); self.send_header("Content-Range",f"bytes */{size}"); self.send_header("Accept-Ranges","bytes"); self.send_header("Content-Length","0"); self.end_headers(); return
        length=0 if size==0 else end-start+1
        self.send_response(206 if partial else 200)
        self.send_header("Content-Type",media_type or "application/octet-stream")
        self.send_header("Content-Length",str(length)); self.send_header("Accept-Ranges","bytes")
        self.send_header("Cache-Control","no-store")
        if partial: self.send_header("Content-Range",f"bytes {start}-{end}/{size}")
        self.end_headers()
        if head or length<=0: return
        with source.open("rb") as fh:
            fh.seek(start); remaining=length
            while remaining>0:
                chunk=fh.read(min(1024*1024,remaining))
                if not chunk: break
                self.wfile.write(chunk); remaining-=len(chunk)

    def _serve_media_item(self,target,entry_id,*,head=False):
        """Serve one catalog item by owner+entry id without requiring SHA promotion.

        This is the ordinary playback path. Hashing remains an explicit identity/artifact
        operation rather than a prerequisite for listening to already-scanned music.
        """
        target=str(target or "").strip(); entry_id=str(entry_id or "").strip(); local=identity()["name"]
        if not entry_id:
            if head:
                self.send_response(400); self.send_header("Content-Length","0"); self.end_headers(); return
            return self.sendj(400,{"error":"media entry id required"})
        if not target or target==local:
            try:
                row,source=_local_media_entry(entry_id)
                ctype=str(row.get("media_type") or mimetypes.guess_type(str(source))[0] or "application/octet-stream")
                return self._serve_file_range(source,ctype,head=head)
            except Exception as exc:
                if head:
                    self.send_response(404); self.send_header("Content-Length","0"); self.end_headers(); return
                return self.sendj(404,{"error":str(exc)})
        snapshot={"self":node_info(),"peers":PEERS.public()}
        try:
            peer=_peer_for_target(snapshot,target); last_exc=None
            for base in _peer_bases(peer):
                url=base+"/v1/media/item?id="+urllib.parse.quote(entry_id,safe="")
                headers=FABRIC_IDENTITY.auth_headers_for_url(url)
                if self.headers.get("Range"): headers["Range"]=self.headers.get("Range")
                req=urllib.request.Request(url,headers=headers,method="HEAD" if head else "GET")
                context=FABRIC_IDENTITY.ssl_context_for_url(url) if url.lower().startswith("https://") else None
                try:
                    kwargs={"timeout":8.0}
                    if context is not None: kwargs["context"]=context
                    with urllib.request.urlopen(req,**kwargs) as r:
                        self.send_response(getattr(r,"status",200))
                        for key in ("Content-Type","Content-Length","Accept-Ranges","Content-Range","Cache-Control"):
                            value=r.headers.get(key)
                            if value: self.send_header(key,value)
                        self.end_headers()
                        if not head:
                            while True:
                                chunk=r.read(256*1024)
                                if not chunk: break
                                self.wfile.write(chunk)
                        return
                except Exception as exc:
                    last_exc=exc
            raise RuntimeError(f"media item transport failed: {last_exc}")
        except urllib.error.HTTPError as exc:
            self.send_response(exc.code); self.send_header("Content-Length","0"); self.end_headers()
        except Exception as exc:
            if head:
                self.send_response(502); self.send_header("Content-Length","0"); self.end_headers(); return
            self.sendj(502,{"error":str(exc)})


    def _serve_media_artifact(self,target,digest,*,head=False):
        """Expose one artifact through the local control plane.

        Players receive a boring loopback URL. This node owns Fabric auth, pinned
        TLS, Tailcat/Tailscale fallback, Range forwarding, and remote retries.
        """
        target=str(target or "").strip(); digest=str(digest or "").strip(); local=identity()["name"]
        if not digest:
            if head:
                self.send_response(400); self.send_header("Content-Length","0"); self.end_headers(); return
            return self.sendj(400,{"error":"artifact digest required"})
        if not target or target==local:
            return self._serve_artifact(digest,head=head)
        snapshot={"self":node_info(),"peers":PEERS.public()}
        try:
            peer=_peer_for_target(snapshot,target); last_exc=None
            for base in _peer_bases(peer):
                url=base+"/v1/artifacts/"+urllib.parse.quote(digest,safe=":")
                headers=FABRIC_IDENTITY.auth_headers_for_url(url)
                if self.headers.get("Range"):
                    headers["Range"]=self.headers.get("Range")
                req=urllib.request.Request(url,headers=headers,method="HEAD" if head else "GET")
                context=FABRIC_IDENTITY.ssl_context_for_url(url) if url.lower().startswith("https://") else None
                try:
                    kwargs={"timeout":8.0}
                    if context is not None: kwargs["context"]=context
                    with urllib.request.urlopen(req,**kwargs) as r:
                        self.send_response(getattr(r,"status",200))
                        for key in ("Content-Type","Content-Length","Accept-Ranges","Content-Range","Cache-Control","X-Fabric-Digest"):
                            value=r.headers.get(key)
                            if value: self.send_header(key,value)
                        self.end_headers()
                        if not head:
                            while True:
                                chunk=r.read(256*1024)
                                if not chunk: break
                                self.wfile.write(chunk)
                        return
                except Exception as exc:
                    last_exc=exc
            raise RuntimeError(f"artifact transport failed: {last_exc}")
        except urllib.error.HTTPError as exc:
            self.send_response(exc.code); self.send_header("Content-Length","0"); self.end_headers()
        except Exception as exc:
            if head:
                self.send_response(502); self.send_header("Content-Length","0"); self.end_headers(); return
            self.sendj(502,{"error":str(exc)})

    def _serve_media_audio(self,target,index,*,head=False):
        target=str(target or "").strip(); local=identity()["name"]
        if not target or target==local:
            try:
                source,ctype=_local_media_audio_path(index)
                return self._serve_file_range(source,ctype,head=head)
            except Exception as exc:
                if head:
                    self.send_response(404); self.send_header("Content-Length","0"); self.end_headers(); return
                return self.sendj(404,{"error":str(exc)})
        snapshot={"self":node_info(),"peers":PEERS.public()}
        try:
            peer=_peer_for_target(snapshot,target); last_exc=None
            for base in _peer_bases(peer):
                url=base+"/v1/media/audio?index="+str(int(index))
                headers=FABRIC_IDENTITY.auth_headers_for_url(url)
                if self.headers.get("Range"): headers["Range"]=self.headers.get("Range")
                req=urllib.request.Request(url,headers=headers,method="HEAD" if head else "GET")
                context=FABRIC_IDENTITY.ssl_context_for_url(url) if url.lower().startswith("https://") else None
                try:
                    kwargs={"timeout":8.0}
                    if context is not None: kwargs["context"]=context
                    with urllib.request.urlopen(req,**kwargs) as r:
                        self.send_response(getattr(r,"status",200))
                        for key in ("Content-Type","Content-Length","Accept-Ranges","Content-Range","Cache-Control"):
                            value=r.headers.get(key)
                            if value: self.send_header(key,value)
                        self.end_headers()
                        if not head:
                            while True:
                                chunk=r.read(256*1024)
                                if not chunk: break
                                self.wfile.write(chunk)
                        return
                except Exception as exc:
                    last_exc=exc
            raise RuntimeError(f"media transport failed: {last_exc}")
        except urllib.error.HTTPError as exc:
            self.send_response(exc.code); self.send_header("Content-Length","0"); self.end_headers()
        except Exception as exc:
            if head:
                self.send_response(502); self.send_header("Content-Length","0"); self.end_headers(); return
            self.sendj(502,{"error":str(exc)})

    def do_HEAD(self):
        parsed=urlparse(self.path); path=parsed.path
        if not self._authorized_ingress(path): return
        if path == "/v1/media/item":
            q=parse_qs(parsed.query); target=str((q.get("node") or [""])[0]); entry_id=str((q.get("id") or [""])[0])
            return self._serve_media_item(target,entry_id,head=True)
        if path == "/v1/media/audio":
            q=parse_qs(parsed.query); target=str((q.get("node") or [""])[0]); index=int((q.get("index") or [0])[0] or 0)
            return self._serve_media_audio(target,index,head=True)
        if path == "/v1/media/artifact":
            q=parse_qs(parsed.query); target=str((q.get("node") or [""])[0]); digest=str((q.get("digest") or [""])[0])
            return self._serve_media_artifact(target,digest,head=True)
        if path.startswith("/v1/artifacts/"):
            digest = path.split("/", 3)[3]
            return self._serve_artifact(digest, head=True)
        self.send_response(404)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path
        if not self._authorized_ingress(path): return
        if path in ("/health", "/v1/health"):
            db = FABRIC_STORE.health()
            worker_age = max(0.0, now() - float(WORKER_HEALTH.get("last_loop") or 0))
            worker_ok = bool(WORKER_HEALTH.get("alive")) and worker_age < 3.0
            ok = bool(db.get("ok")) and worker_ok
            return self.sendj(200 if ok else 503, {
                "ok": ok, "version": VERSION, "pulse": pulse_number(),
                "database": db,
                "job_worker": {"ok": worker_ok, "last_loop_age_ms": int(worker_age*1000),
                               "last_error": WORKER_HEALTH.get("last_error"),
                               "errors": WORKER_HEALTH.get("errors", 0)},
            })
        if path == "/v1/http":
            ingress_guard = {"ok": False, "error": "ingress guard unavailable"}
            try:
                ingress_guard = http_json("http://127.0.0.1:7333/_fcl/metrics", timeout=.35)
            except Exception as exc:
                ingress_guard = {"ok": False, "error": str(exc)}
            return self.sendj(200, {"listeners": {name: meter.public() for name, meter in HTTP_METRICS.items()},
                                    "local_port": DEFAULT_PORT, "ingress_port": 7333,
                                    "ingress_guard": ingress_guard})
        if path == "/v1/endpoints/fabric":
            if getattr(self.server,"plane","local") != "local":
                return self.sendj(403,{"error":"Fabric endpoint aggregation is local-control only"})
            return self.sendj(200,_fabric_endpoints())
        if path == "/v1/endpoints":
            return self.sendj(200, _local_endpoints_payload())
        if path == "/v1/identity":
            ident = identity()
            return self.sendj(200, {"schema":"fabric-identity-v1", "identity": {
                k: ident.get(k) for k in ("node_id","fingerprint","algorithm","public_key","name","hostname") if ident.get(k)
            }})
        if path == "/v1/identity/trust":
            if getattr(self.server, "plane", "local") != "local":
                return self.sendj(403, {"error":"trust store is local-only"})
            return self.sendj(200, FABRIC_IDENTITY.trusted(public=True))
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
        if path == "/v1/decisions/provider":
            status=decision_provider_status()
            status["reachable"]=bool(probe("127.0.0.1",8791)) if status.get("enabled") else False
            if status.get("reachable") and status.get("state") == "configured": status["state"]="ready"
            elif status.get("enabled") and not status.get("reachable"): status["state"]="down"
            return self.sendj(200,status)
        if path == "/v1/decisions":
            return self.sendj(200, {"decisions": FABRIC_STORE.decisions(pending_only=True), "node": identity()["name"]})
        if path == "/v1/decisions/fabric":
            return self.sendj(200, _fabric_decisions())
        if path.startswith("/v1/decisions/"):
            did=path.split("/",3)[3]
            decision=FABRIC_STORE.get_decision(did)
            return self.sendj(200,{"decision":decision}) if decision else self.sendj(404,{"error":"decision not found"})
        if path == "/v1/models/curation":
            return self.sendj(200, curator_status())
        if path == "/v1/models/benchmark-guard":
            return self.sendj(200, benchmark_guard_state())
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
        if path == "/v1/memory":
            return self.sendj(200, FABRIC_MEMORY.public(include_local=True))
        if path == "/v1/lights":
            events = FABRIC_STORE.recent_events(limit=96)
            return self.sendj(200, {"pulse": pulse_number(), "light": _active_beacon(events)})
        if path == "/v1/events":
            q = parse_qs(urlparse(self.path).query)
            if "since" not in q:
                return self.sendj(200, {"events": FABRIC_STORE.recent_events()})
            try: since = int((q.get("since") or [0])[0])
            except Exception: since = 0
            return self.sendj(200, {"events": FABRIC_STORE.events(since=since)})
        if path == "/v1/web/search/local":
            q=parse_qs(urlparse(self.path).query); query=str((q.get("q") or [""])[0])
            try: limit=max(1,min(20,int((q.get("limit") or [8])[0])))
            except Exception: limit=8
            result=_local_web_search(query,limit)
            return self.sendj(200 if not result.get("error") else 503,result)
        if path == "/v1/web/search":
            q=parse_qs(urlparse(self.path).query); query=str((q.get("q") or [""])[0])
            try: limit=max(1,min(20,int((q.get("limit") or [8])[0])))
            except Exception: limit=8
            result=_fabric_web_search(query,limit)
            return self.sendj(200 if not result.get("error") else 503,result)
        if path == "/v1/files/catalog":
            return self.sendj(200, _local_file_catalog())
        if path == "/v1/files/search":
            q=parse_qs(urlparse(self.path).query); query=str((q.get("q") or [""])[0]);
            try: limit=max(1,min(200,int((q.get("limit") or [80])[0])))
            except Exception: limit=80
            return self.sendj(200, _local_file_search(query,limit))
        if path == "/v1/files/find":
            q=parse_qs(urlparse(self.path).query); query=str((q.get("q") or [""])[0]);
            return self.sendj(200, _fabric_file_search(query,80))
        if path == "/v1/files/fabric":
            return self.sendj(200, _fabric_file_catalog())
        if path == "/v1/media/catalog":
            return self.sendj(200, _local_media_catalog())
        if path == "/v1/media/fabric":
            return self.sendj(200, _fabric_media_catalog())
        if path == "/v1/media/item":
            q=parse_qs(urlparse(self.path).query); target=str((q.get("node") or [""])[0]); entry_id=str((q.get("id") or [""])[0])
            return self._serve_media_item(target,entry_id)
        if path == "/v1/media/audio":
            q=parse_qs(urlparse(self.path).query); target=str((q.get("node") or [""])[0])
            try: index=int((q.get("index") or [0])[0] or 0)
            except Exception: index=0
            return self._serve_media_audio(target,index)
        if path == "/v1/media/artifact":
            q=parse_qs(urlparse(self.path).query); target=str((q.get("node") or [""])[0]); digest=str((q.get("digest") or [""])[0])
            return self._serve_media_artifact(target,digest)
        if path == "/v1/media/output":
            return self.sendj(200, _local_media_output())
        if path == "/v1/media/outputs":
            return self.sendj(200, _fabric_media_outputs())
        if path == "/v1/media/state":
            return self.sendj(200, _local_media_state())
        if path == "/v1/media/session-full":
            try:
                return self.sendj(200, _local_media_full_session())
            except Exception as exc:
                return self.sendj(502, {"error":str(exc)})
        if path == "/v1/media/session":
            q = parse_qs(urlparse(self.path).query)
            target = str((q.get("node") or [""])[0])
            try:
                return self.sendj(200, _fabric_media_state(target))
            except Exception as exc:
                return self.sendj(502, {"available": False, "active": False, "state": "unavailable", "queue": [], "node": target, "error": str(exc)})
        if path == "/v1/artifacts":
            return self.sendj(200, _local_artifact_catalog())
        if path == "/v1/artifacts/fabric":
            return self.sendj(200, _fabric_artifact_catalog())
        if path == "/v1/ui/state":
            db = FABRIC_STORE.health()
            worker_age = max(0.0, now() - float(WORKER_HEALTH.get("last_loop") or 0))
            worker_ok = bool(WORKER_HEALTH.get("alive")) and worker_age < 3.0
            snapshot = {
                "nodes": {"self": node_info(), "peers": PEERS.public()},
                "health": {"ok": bool(db.get("ok")) and worker_ok},
                "jobs": {"jobs": FABRIC_STORE.jobs()},
                "decisions": {"decisions": FABRIC_STORE.decisions(pending_only=True)},
                "services": {"services": managed_services()},
                "events": {"events": FABRIC_STORE.recent_events()},
            }
            return self.sendj(200, build_ui_model(snapshot))
        if path.startswith("/v1/artifacts/"):
            digest = path.split("/", 3)[3]
            q = parse_qs(urlparse(self.path).query)
            if str((q.get("meta") or [""])[0]).casefold() in {"1", "true", "yes"}:
                try:
                    meta = ARTIFACTS.metadata(digest)
                    # path_for validates that a file-backed artifact still points at
                    # the bytes it advertised, without loading the media into RAM.
                    ARTIFACTS.path_for(digest)
                    return self.sendj(200, {"artifact": _artifact_public_metadata(meta)})
                except Exception:
                    return self.sendj(404, {"error": "artifact not found"})
            return self._serve_artifact(digest)
        return self.sendj(404, {"error": "not found"})

    def do_POST(self):
        path = urlparse(self.path).path
        if not self._authorized_ingress(path): return
        d = self.body()
        if path == "/v1/endpoints/fabric/allow":
            if getattr(self.server,"plane","local") != "local":
                return self.sendj(403,{"error":"Fabric endpoint management is local-control only"})
            try:
                result=_endpoint_allow_fabric(str(d.get("code") or ""),str(d.get("mode") or "once"))
                return self.sendj(200,{"ok":True,**result})
            except ValueError as exc:
                return self.sendj(404,{"ok":False,"error":str(exc)})
        if path == "/v1/endpoints/fabric/revoke":
            if getattr(self.server,"plane","local") != "local":
                return self.sendj(403,{"error":"Fabric endpoint management is local-control only"})
            result=_endpoint_revoke_fabric(str(d.get("endpoint_id") or ""))
            return self.sendj(200 if result.get("ok") else 404,result)
        if path == "/v1/endpoints/allow":
            try:
                row=ENDPOINT_AUTH.allow(str(d.get("code") or ""),str(d.get("mode") or "once"))
                return self.sendj(200,{"ok":True,"endpoint":row,"node":identity()["name"]})
            except ValueError as exc:
                return self.sendj(404,{"ok":False,"error":str(exc)})
        if path == "/v1/endpoints/revoke":
            ok=ENDPOINT_AUTH.revoke(str(d.get("endpoint_id") or ""))
            return self.sendj(200 if ok else 404,{"ok":ok,"node":identity()["name"],"error":None if ok else "endpoint not found"})
        if path == "/v1/identity/pair":
            try:
                peer=d.get("identity") if isinstance(d,dict) else None
                accepted=FABRIC_IDENTITY.accept_pairing(str(d.get("code") or ""), peer,
                    auth_token=str(d.get("auth_token") or ""), peer_endpoint=str(d.get("endpoint") or "") or None)
                me=identity()
                public={k:me.get(k) for k in ("node_id","fingerprint","algorithm","public_key","name","hostname","transports") if me.get(k)}
                local_transports=FABRIC_IDENTITY.local_transports()
                if local_transports: public["transports"]=local_transports
                FABRIC_STORE.event(None,"identity","paired",accepted.get("node_id"),node=identity()["name"],
                    data={"peer":accepted.get("name"),"node_id":accepted.get("node_id"),"fingerprint":accepted.get("fingerprint")})
                return self.sendj(201,{"ok":True,"schema":"fabric-pair-v1","identity":public})
            except (ValueError,RuntimeError) as exc:
                return self.sendj(403,{"ok":False,"error":str(exc)})
        if path == "/v1/decisions":
            try:
                req=new_decision_request(
                    question=str(d.get("question") or ""),
                    choices=d.get("choices") or [],
                    profile=str(d.get("profile") or "workspace"),
                    confidence=float(d.get("confidence") or 0.0),
                    margin=float(d.get("margin") or 0.0),
                    consequence=str(d.get("consequence") or "low"),
                    reversible=bool(d.get("reversible",True)),
                    preferred=d.get("preferred"), fallback=d.get("fallback"),
                    deadline_seconds=d.get("deadline_seconds"),
                    origin=str(d.get("origin") or identity()["name"]),
                    job_id=d.get("job_id"), channels=d.get("channels"),
                    context=d.get("context") if isinstance(d.get("context"),dict) else {},
                    provider=str(d.get("provider") or "deterministic"),
                )
                shadow=None
                if bool(d.get("shadow_openjev")):
                    labels=[str(x.get("label") or x.get("value")) for x in req.get("choices") or []]
                    shadow=_openjev_shadow(str((req.get("context") or {}).get("state") or ""),req["question"],labels)
                    req["shadow"]={"openjev":shadow}
                stored=FABRIC_STORE.add_decision(req,node=identity()["name"])
                return self.sendj(201,{"ok":True,"decision":stored,"shadow":shadow})
            except (ValueError,TypeError) as exc:
                return self.sendj(400,{"ok":False,"error":str(exc)})
        if path == "/v1/decisions/answer":
            try:
                result=_decision_answer_fabric(d.get("node"),str(d.get("id") or ""),str(d.get("selected") or ""),str(d.get("source") or "human"))
                return self.sendj(200,{"ok":True,**result})
            except KeyError:
                return self.sendj(404,{"ok":False,"error":"decision not found"})
            except ValueError as exc:
                return self.sendj(400,{"ok":False,"error":str(exc)})
            except Exception as exc:
                return self.sendj(502,{"ok":False,"error":str(exc)})
        if path == "/v1/decisions/shadow":
            candidates=d.get("candidates") or []
            if not isinstance(candidates,list) or len(candidates)<2:
                return self.sendj(400,{"ok":False,"error":"at least two candidates required"})
            return self.sendj(200,_openjev_shadow(str(d.get("state") or ""),str(d.get("question") or "Choose the best option."),[str(x) for x in candidates],
                profile=str(d.get("profile") or "workspace"),consequence=str(d.get("consequence") or "low"),reversible=bool(d.get("reversible",True))))
        if path == "/v1/memory":
            try:
                action=str(d.get("action") or "merge").lower()
                if action == "add":
                    item=FABRIC_MEMORY.add(str(d.get("scope") or "shared"), str(d.get("text") or ""), int(d.get("importance") or 60), identity()["name"])
                    return self.sendj(200, {"ok":True,"item":item})
                if action == "merge":
                    return self.sendj(200, FABRIC_MEMORY.merge(d.get("items") or []))
                if action == "sync":
                    return self.sendj(200, _memory_sync())
                return self.sendj(400, {"ok":False,"error":"memory action must be add, merge, or sync"})
            except ValueError as exc:
                return self.sendj(400, {"ok":False,"error":str(exc)})
        if path == "/v1/beacon":
            try:
                if d.get("start_pulse"):
                    return self.sendj(200, _beacon_record(d))
                return self.sendj(200, _beacon_broadcast(str(d.get("pattern") or "rgb"), int(d.get("lead_pulses") or 3)))
            except ValueError as exc:
                return self.sendj(400, {"ok": False, "error": str(exc)})
        if path == "/v1/lights":
            try:
                return self.sendj(200, _lights_broadcast(
                    str(d.get("pattern") or "demo"), show_id=d.get("show_id"),
                    start_pulse=d.get("start_pulse"), repeat=bool(d.get("repeat")),
                    lease_pulses=int(d.get("lease_pulses") or 8), stopped=bool(d.get("stopped"))))
            except ValueError as exc:
                return self.sendj(400, {"ok": False, "error": str(exc)})
        if path == "/v1/infer/stream":
            try:
                return _stream_model_infer(self, d)
            except PermissionError as exc:
                return self.sendj(403, {"ok":False,"error":str(exc)})
            except ValueError as exc:
                return self.sendj(400, {"ok":False,"error":str(exc)})
            except Exception as exc:
                return self.sendj(409, {"ok":False,"error":str(exc)})
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
        if path == "/v1/models/benchmark-guard":
            state=benchmark_guard_set(bool(d.get("active")), d.get("ttl") or 3600, d.get("reason") or "operator benchmark")
            return self.sendj(200,{"ok":True,**state})
        if path == "/v1/models/curation":
            state=load_curator_state()
            mode=str(d.get("mode") or state.get("mode") or "observe").lower()
            profile=str(d.get("profile") or state.get("profile") or "balanced").lower()
            if mode not in {"observe","auto"}:
                return self.sendj(400,{"ok":False,"error":"mode must be observe or auto"})
            if profile not in {"reflex","balanced","deep"}:
                return self.sendj(400,{"ok":False,"error":"profile must be reflex, balanced, or deep"})
            state.update(mode=mode,profile=profile)
            save_curator_state(state)
            if d.get("apply"):
                with CURATOR_LOCK:
                    result=curator_apply(profile,reason=str(d.get("reason") or "operator apply"))
                result["state"]=load_curator_state()
                return self.sendj(200 if result.get("ok") else 409,result)
            return self.sendj(200,{"ok":True,"state":state,"plan":curator_plan(profile)})
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
        if path == "/v1/media/route":
            try:
                target = str(d.get("node") or "").strip()
                operation = str(d.get("operation") or "").strip()
                payload = {k:v for k,v in d.items() if k not in {"node", "operation"}}
                if operation=="move":
                    return self.sendj(200,_fabric_media_move(str(d.get("source") or ""),target or str(d.get("target") or ""),d.get("index")))
                return self.sendj(200, _fabric_media_route(target, operation, payload))
            except ValueError as exc:
                return self.sendj(400, {"ok": False, "error": str(exc)})
            except Exception as exc:
                return self.sendj(502, {"ok": False, "error": str(exc)})
        if path == "/v1/media/identify":
            try:
                return self.sendj(200, _identify_media_entry(d.get("id")))
            except FileNotFoundError:
                return self.sendj(404, {"ok": False, "error": "media entry not found"})
            except Exception as exc:
                return self.sendj(400, {"ok": False, "error": str(exc)})
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


def _endpoint_allow_cli_fallback(host, port, code, mode):
    """6.1 migration fallback: route an endpoint approval from the CLI itself.

    This also makes endpoint management resilient when LOOK has upgraded before the
    resident node process has restarted onto the Fabric-wide endpoint routes.
    """
    snapshot=_daemon_get(host,port,"/v1/nodes")
    local_name=str((snapshot.get("self") or {}).get("name") or identity().get("name") or "local")
    candidates=[("local",_daemon_url(host,port,""))]
    for peer in snapshot.get("peers") or []:
        ad=peer.get("node") or {}; name=((ad.get("identity") or {}).get("name") or peer.get("name"))
        base=_peer_base(peer)
        if name and base: candidates.append((str(name),base))
    found=[]
    for name,base in candidates:
        try:
            data=http_json(base+"/v1/endpoints",timeout=2.0)
        except Exception:
            continue
        if any(str(row.get("code") or "")==str(code) for row in (data.get("pending") or [])):
            found.append((name,base))
    if not found: raise RuntimeError("endpoint code not found or expired anywhere in the reachable Fabric")
    if len(found)>1: raise RuntimeError("endpoint code is ambiguous across Fabric nodes")
    name,base=found[0]
    result=http_json(base+"/v1/endpoints/allow",{"code":str(code),"mode":str(mode)},timeout=4.0)
    return {"ok":True,"node":name,"endpoint":result.get("endpoint") or {}}


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


def _peer_bases(peer):
    """Ordered usable transports for a peer: active/direct first, then fallbacks."""
    out=[]
    if peer.get("url"): out.append(str(peer["url"]).rstrip("/"))
    for value in peer.get("tailcat_endpoints") or []:
        value=str(value).rstrip("/")
        if value and value not in out: out.append(value)
    if peer.get("dns"):
        value=f"https://{peer['dns']}:7332"
        if value not in out: out.append(value)
    return out


def _peer_for_target(snapshot,target):
    needle=str(target or "").casefold()
    for peer in snapshot.get("peers") or []:
        names={str(peer.get("name") or "").casefold(),str((peer.get("node") or {}).get("identity",{}).get("name") or "").casefold()}
        if needle in names: return peer
    raise RuntimeError(f"Fabric node not found: {target}")


def _peer_base(peer):
    if peer.get("url"):
        return str(peer["url"]).rstrip("/")
    if peer.get("tailcat_endpoints"):
        return str(peer["tailcat_endpoints"][0]).rstrip("/")
    if peer.get("dns"):
        return f"https://{peer['dns']}:7332"
    return ""


def _remote_url(snapshot, target, path):
    local=(snapshot.get("self") or {}).get("name")
    if target in {None, "", "local", local}:
        return _daemon_url(DEFAULT_HOST, DEFAULT_PORT, path)
    needle=str(target).lower()
    for peer in snapshot.get("peers") or []:
        names={str(peer.get("name") or "").lower(), str((peer.get("node") or {}).get("identity",{}).get("name") or "").lower()}
        if needle in names and peer.get("node"):
            if peer.get("url"):
                return str(peer["url"]).rstrip("/")+path
            if peer.get("tailcat_endpoints"):
                return str(peer["tailcat_endpoints"][0]).rstrip("/")+path
            if peer.get("dns"):
                return f"https://{peer['dns']}:7332{path}"
    raise RuntimeError(f"Fabric node not found or not advertising: {target}")


def _target_get(host, port, target, path):
    # Local control never needs peer discovery. Keep simple diagnostics usable
    # even when the network side of the Fabric is unhealthy.
    if target in {None,"","local"}:
        return _daemon_get(host,port,path)
    snap=_daemon_get(host,port,"/v1/nodes")
    local=(snap.get("self") or {}).get("name")
    if target == local:
        return _daemon_get(host,port,path)
    url=_remote_url(snap,target,path)
    return http_json(url,timeout=4.0)


def _target_post(host, port, target, path, payload, timeout=45.0):
    if target in {None,"","local"}:
        return http_json(_daemon_url(host,port,path),payload,timeout=timeout)
    snap=_daemon_get(host,port,"/v1/nodes")
    local=(snap.get("self") or {}).get("name")
    if target == local:
        return http_json(_daemon_url(host,port,path),payload,timeout=timeout)
    url=_remote_url(snap,target,path)
    return http_json(url,payload,timeout=timeout)


def _print_models(data, target="local"):
    print(f"FABRIC MODELS · {target}")
    print("─"*176)
    print(f"{'MODEL':<27} {'STATE':<9} {'LIVE TEST':<14} {'TTFT':>7} {'TOK/S':>7} {'BENCH':<9} {'PURPOSE EVIDENCE':<30} {'TOOLS':>7} {'AGENT':>7} {'EXACT':>7}")
    for m in data.get("models") or []:
        q=m.get("qualification") or {}; b=m.get("benchmark") or {}
        state="resident" if m.get("resident") else "available"
        rate=q.get("generation_tok_s"); ttft=q.get("ttft_ms")
        test=_qualification_label(m)
        ttft_text=f"{int(ttft)}ms" if isinstance(ttft,(int,float)) else "—"
        rate_text=f"{float(rate):.1f}" if isinstance(rate,(int,float)) else "—"
        bench_state,_=_benchmark_state(m)
        bench=(str(b.get("fit") or "ERROR").upper() if bench_state!="untested" else "untested")
        purpose=_purpose_label(m,compact=True) or "—"
        tools=(f"{b.get('tools')}/3" if isinstance(b.get('tools'),int) else "—")
        agent=("yes" if b.get("agent") else "no") if b.get("tested_at") else "—"
        exact=("yes" if b.get("exact") else "no") if b.get("tested_at") else "—"
        print(f"{str(m.get('name') or '?'):<27.27} {state:<9} {test:<14.14} {ttft_text:>7} {rate_text:>7} "
              f"{bench:<9.9} {purpose:<30.30} {tools:>7} {agent:>7} {exact:>7}")


def _watch(host,port,interval=1.0):
    cursors = {}
    next_peer_poll = {}
    live_events = []
    try:
        while True:
            snap=_daemon_get(host,port,"/v1/nodes")
            sources=[("local",_daemon_url(host,port,""))]
            for peer in snap.get("peers") or []:
                if peer.get("node") and _peer_base(peer):
                    sources.append((peer.get("name") or "peer",_peer_base(peer)))
            tnow = now()
            for name,base in sources:
                remote = base.startswith("https://")
                if remote and tnow < float(next_peer_poll.get(name) or 0):
                    continue
                if remote:
                    next_peer_poll[name] = tnow + WATCH_PEER_REFRESH_SECONDS
                try:
                    # First contact joins the live tail. Reconnects continue from the
                    # cursor only while this watch process is alive; an overnight gap
                    # never becomes thousands of historical events to drain/render.
                    if name not in cursors:
                        data=http_json(f"{base}/v1/events",timeout=.8)
                    else:
                        data=http_json(f"{base}/v1/events?since={cursors[name]}",timeout=.8)
                    events=data.get("events") or []
                    if events:
                        cursors[name]=max(int(e.get("seq") or 0) for e in events)
                        for e in events[-14:]:
                            e=dict(e); e["source"]=name; live_events.append(e)
                    elif name not in cursors:
                        cursors[name]=0
                except Exception:
                    if remote:
                        next_peer_poll[name] = tnow + max(5.0, WATCH_PEER_REFRESH_SECONDS * 2)
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




def _dash_age(seconds):
    try:
        seconds = max(0, int(seconds))
    except Exception:
        return "?"
    if seconds < 60:
        return f"{seconds}s"
    if seconds < 3600:
        return f"{seconds // 60}m"
    return f"{seconds // 3600}h"


def _qualification_state(model, current=None):
    """Classify lightweight node qualification without inventing an IQ score."""
    q = (model or {}).get("qualification") or {}
    tested_at = float(q.get("tested_at") or 0)
    if not tested_at:
        return "untested", None
    age = max(0.0, (now() if current is None else float(current)) - tested_at)
    if not q.get("ok"):
        return "failed", age
    if age >= QUALIFY_RECHECK_SECONDS:
        return "stale", age
    return "qualified", age


def _qualification_label(model, current=None, compact=False):
    state, age = _qualification_state(model, current=current)
    if state == "untested":
        return "—" if compact else "untested"
    age_text = _dash_age(age)
    if state == "qualified":
        return f"Q {age_text}" if compact else f"qualified {age_text}"
    if state == "stale":
        return f"S {age_text}" if compact else f"stale {age_text}"
    return f"! {age_text}" if compact else f"failed {age_text}"


def _benchmark_state(model):
    b=(model or {}).get("benchmark") or {}
    if not b.get("tested_at"):
        return "untested", None
    age=max(0.0, now()-float(b.get("tested_at") or 0))
    if b.get("fatal_error") or b.get("speed_error") or str(b.get("fit") or "").upper()=="ERROR":
        return "failed", age
    return "benchmarked", age


def _benchmark_label(model, compact=False):
    state,age=_benchmark_state(model)
    if state=="untested":
        return "B—" if compact else "unbenchmarked"
    if state=="failed":
        return f"B! {_dash_age(age)}" if compact else f"benchmark failed {_dash_age(age)}"
    b=(model or {}).get("benchmark") or {}
    fit=str(b.get("fit") or "?").upper()
    tools=b.get("tools")
    agent=b.get("agent")
    exact=b.get("exact")
    if compact:
        bits=[f"B:{fit[:4]}"]
        if isinstance(tools,int): bits.append(f"T{tools}/3")
        if agent is not None: bits.append("A✓" if agent else "A·")
        if exact is not None: bits.append("E✓" if exact else "E·")
        return " ".join(bits)
    return f"{fit} · tools {tools if isinstance(tools,int) else '—'}/3 · agent {'yes' if agent else 'no'} · exact {'yes' if exact else 'no'} · {_dash_age(age)}"


def _model_short_name(name):
    """Human-scale model identity for dense Dash residency lists."""
    name=str(name or "").strip()
    if not name:
        return "?"
    base,sep,tag=name.partition(":")
    low=base.casefold()
    family=base
    for prefix,short in (("qwen", "q"), ("gemma", "g"), ("llama", "l"),
                         ("deepseek", "d"), ("mistral", "m"), ("phi", "p")):
        if low.startswith(prefix):
            family=short + base[len(prefix):]
            break
    family=family.replace("-", "")
    return f"{family}:{tag}" if sep and tag else family


def _purpose_label(model, compact=False):
    """Expose benchmark evidence by purpose without pretending it is one IQ score."""
    b=(model or {}).get("benchmark") or {}
    if not b.get("tested_at"):
        return ""
    exact=b.get("exact")
    ttft=b.get("ttft")
    rate=b.get("rate")
    reflex_parts=[]
    if exact is not None:
        reflex_parts.append(bool(exact))
    if isinstance(ttft,(int,float)):
        reflex_parts.append(float(ttft) <= 2.5)
    if isinstance(rate,(int,float)) and float(rate) > 0:
        reflex_parts.append(float(rate) >= 40.0)
    reflex=sum(reflex_parts) if reflex_parts else None
    reasoning=b.get("reasoning")
    tools=b.get("tools")
    agent=b.get("agent")
    if compact:
        bits=[]
        if reflex is not None: bits.append(f"RFX{reflex}/{len(reflex_parts)}")
        if isinstance(reasoning,int): bits.append(f"RSN{reasoning}/3")
        if isinstance(tools,int): bits.append(f"T{tools}/3")
        if agent is not None: bits.append("A✓" if agent else "A·")
        return " ".join(bits)
    bits=[]
    if reflex is not None: bits.append(f"reflex {reflex}/{len(reflex_parts)}")
    if isinstance(reasoning,int): bits.append(f"reasoning {reasoning}/3")
    if isinstance(tools,int): bits.append(f"tools {tools}/3")
    if agent is not None: bits.append(f"agent {'yes' if agent else 'no'}")
    return " · ".join(bits)


def _dash_model(node):
    """Compact model truth: configured model, exact residency, live qualification and benchmark evidence."""
    inf = node.get("inference") or {}
    models = inf.get("models") or []
    preferred = str(inf.get("preferred_model") or "")
    resident = [str(x) for x in (inf.get("resident") or []) if str(x)]
    by_name = {str(m.get("name") or ""): m for m in models if m.get("name")}
    primary_name = preferred or (resident[0] if resident else (next(iter(by_name), "")))
    if not primary_name:
        return "—"
    primary = by_name.get(primary_name) or {}
    if not resident:
        residency = "cold"
    elif len(resident)==1 and resident[0]==primary_name:
        residency = "R"
    else:
        residency = "R[" + ",".join(_model_short_name(x) for x in resident) + "]"
        if primary_name not in resident:
            residency = "cold+" + residency
    qualification = _qualification_label(primary, compact=True)
    rate = ((primary.get("qualification") or {}).get("generation_tok_s"))
    perf = f"{rate:g}t/s" if isinstance(rate, (int, float)) else ""
    bits = [primary_name, residency, qualification]
    if perf:
        bits.append(perf)
    purpose=_purpose_label(primary,compact=True)
    if purpose:
        bits.append(purpose)
    elif _benchmark_label(primary,compact=True) != "B—":
        bits.append(_benchmark_label(primary,compact=True))
    return " · ".join(bits)


def _dash_state(node):
    active = ((node.get("supervisor") or {}).get("active"))
    if not active:
        return "idle"
    phase = str(active.get("phase") or active.get("state") or "working")
    owner = str(active.get("owner") or "")
    return f"{phase}:{owner}" if owner else phase


def _dash_event_scope(event, local_name):
    """Describe where an observed event happened without pretending ledgers are global."""
    event_node = str((event or {}).get("node") or "")
    if not event_node or event_node == str(local_name or ""):
        return "LOCAL"
    return "REMOTE"


def _dash_event_stamp(ts, current=None):
    """Keep same-day events compact; make stale cross-day rows obvious."""
    current = float(current if current is not None else now())
    stamp = float(ts or current)
    a = time.localtime(stamp)
    b = time.localtime(current)
    if (a.tm_year, a.tm_yday) == (b.tm_year, b.tm_yday):
        return time.strftime("%H:%M:%S", a)
    return time.strftime("%a %H:%M", a)


def _dash_event_flash(event):
    """Map meaningful Fabric state transitions to restrained ambient telemetry.

    Return an ANSI background SGR fragment, or None for noisy/low-value events.
    This is presentation only: producers never emit terminal-color instructions.
    """
    if not event:
        return None
    typ = str(event.get("type") or "").lower()
    phase = str(event.get("phase") or "").lower()
    detail = str(event.get("detail") or "").lower()
    if typ == "release":
        if phase in {"ok", "done", "complete", "completed", "success"}:
            return "42;30"       # green · successful completion
        if phase in {"failed", "error", "denied", "cancelled", "canceled"}:
            return "41;97"       # red · failed/cancelled work
    if typ == "control" and "cancel" in (phase + " " + detail):
        return "41;97"
    if typ == "memory" or phase in {"tool", "capability", "receipt"}:
        return "46;30"           # cyan · deterministic/tool work
    if typ == "decision" and phase in {"judge", "pending"}:
        return "48;5;214;30"     # amber · probabilistic judgment / human input
    if typ == "decision" and phase in {"answered", "timeout"}:
        return "42;30"           # green · uncertainty collapsed / action authorized
    if typ == "decision" and phase in {"provider-down", "error"}:
        return "41;97"           # red · learned worker unavailable; Fabric will degrade
    if typ == "progress":
        if phase == "dispatch":
            return "44;97"       # blue · work accepted/dispatched
        if phase in {"inference", "first-token"}:
            return "48;5;214;30" # amber · model inference
        if phase == "working":
            return "45;97"       # purple · remote/general Fabric work
    return None


def _dash_event_color(event):
    """One semantic color vocabulary for both ambient flashes and RECENT."""
    bg = _dash_event_flash(event)
    return {
        "44;97": ("blue", "34"),
        "48;5;214;30": ("amber", "38;5;214"),
        "46;30": ("cyan", "36"),
        "42;30": ("green", "32"),
        "41;97": ("red", "31"),
        "45;97": ("purple", "35"),
    }.get(bg, (None, None))


def _dash_event_visible(event):
    """Only semantic work belongs in RECENT.

    Beacon/light frames are renderer effects. Showing them as ordinary activity
    makes a diagnostic animation look like work and can create apparent event
    storms when a terminal escape sequence accidentally reaches a hotkey.
    """
    typ = str((event or {}).get("type") or "").lower()
    return typ not in {"beacon", "light", "lights", "rgb", "pulse"}


def _dash_recent_events(events, limit=5):
    visible = [event for event in (events or []) if _dash_event_visible(event)]
    return visible[-max(0, int(limit)):]


def _dash_recent_line(event, local_name, width, ansi=False):
    stamp = _dash_event_stamp(event.get("ts"))
    scope = _dash_event_scope(event, local_name)
    phase = str(event.get("phase") or event.get("type") or "event")[:12]
    detail = str(event.get("detail") or "")[: max(12, width - 38)]
    _, fg = _dash_event_color(event)
    dot = "●" if fg else "·"
    row = f"{dot} {stamp:<9} {scope:<6} {phase:<12} {detail}"
    return f"\033[{fg}m{row}\033[0m" if ansi and fg else row


def _dash_controls(width, mini=False):
    """Render the shared action model into one terminal row.

    Actions are defined once in ``ui_model`` so Signal/Future Crash can eventually
    present the same controls without copying Dash semantics.
    """
    width=max(20,int(width or 80))
    items=[a for a in ui_actions(mini=mini) if not a.get("hidden")]
    # Least important actions disappear first; their hotkeys continue to work.
    drop_order=("restart","doctor","watch","settings","lights","beacon")
    def render(rows):
        return "   ".join(f"[{a['key']}] {a['label']}" for a in rows)
    text=render(items)
    for action_id in drop_order:
        if len(text) <= width:
            break
        items=[a for a in items if a.get("id") != action_id]
        text=render(items)
    return text[:width]


def _dash_visible_len(text):
    return len(re.sub(r"\x1b\[[0-9;]*m", "", str(text)))


def _dash_visual_rows(text, width):
    """Count terminal rows, including accidental wrapping, before choosing a layout."""
    width=max(1,int(width or 1)); total=0
    for line in str(text).splitlines() or [""]:
        total += max(1, (_dash_visible_len(line)+width-1)//width)
    return total


def _dash_render_mini(data, width=44, ansi=False):
    snap = data.get("nodes") or {}
    local = snap.get("self") or {}
    events = (data.get("events") or {}).get("events") or []
    width = max(30, min(int(width or 44), 64))
    rule = "─" * width
    name = str(local.get("name") or "local")
    model = _dash_model(local)
    lines = [f"FABRIC · {name[:max(8,width-12)]}", rule,
             f"{_dash_state(local)[:18]} · {model[:max(8,width-23)]}", "", "RECENT"]
    if events:
        for e in _dash_recent_events(events, 5):
            # Mini favors semantic signal over verbose detail.
            _, fg = _dash_event_color(e)
            phase = str(e.get("phase") or e.get("type") or "event")[:10]
            scope = "L" if _dash_event_scope(e, name) == "LOCAL" else "R"
            detail = str(e.get("detail") or "")[:max(6, width-23)]
            row = f"{'●' if fg else '·'} {_dash_event_stamp(e.get('ts'))[-8:]} {scope} {phase:<10} {detail}"
            lines.append(f"\033[{fg}m{row}\033[0m" if ansi and fg else row)
    else:
        lines.append("· no recent events")
    lines += [rule, _dash_controls(width, mini=True)]
    return "\n".join(lines)


def _dash_capability_summary(data, width=92):
    """Compact capability truth derived from the shared renderer-neutral model."""
    ui=build_ui_model(data)
    caps=ui.get("capabilities") or []
    if not caps:
        return "none advertised"
    preferred=("model.vision","model.tools","ollama","comfyui","filesystem","signal","mercury")
    by_id={str(c.get("id")): c for c in caps}
    ordered=[by_id[x] for x in preferred if x in by_id]
    ordered += [c for c in caps if c not in ordered]
    bits=[]
    for cap in ordered:
        name=str(cap.get("id") or "?").replace("model.", "")
        count=int(cap.get("count") or 0)
        bits.append(f"{name}:{count}")
        if len("  ".join(bits)) >= max(20,int(width)-8):
            bits.pop()
            break
    return "  ".join(bits) or "none advertised"


def _dash_pending_decisions(data):
    return [d for d in ((data.get("decisions") or {}).get("decisions") or [])
            if str(d.get("status") or "pending") == "pending"]


def _dash_decision_line(decision, width=92):
    question=" ".join(str(decision.get("question") or "input requested").split())
    node=str(decision.get("node") or decision.get("origin") or "local")
    remaining=max(0,int(float(decision.get("expires") or now())-now()))
    fallback=str(decision.get("fallback") or "defer")
    prefix=f"INPUT · {node} · {remaining}s · "
    suffix=f" · timeout:{fallback}"
    room=max(12,int(width)-len(prefix)-len(suffix))
    return prefix + question[:room] + suffix


def _dash_decision_summary(data):
    events=(data.get("events") or {}).get("events") or []
    judges=[e for e in events if str(e.get("type") or "") == "decision" and str(e.get("phase") or "") == "judge"]
    pending=len(_dash_pending_decisions(data))
    last=judges[-1] if judges else None
    info=(last or {}).get("data") or {}
    return {"ready":bool(((data.get("nodes") or {}).get("self") or {}).get("capabilities",{}).get("decision.openjev")),
            "last":info.get("choice"),"confidence":info.get("confidence"),"margin":info.get("margin"),
            "latency_ms":info.get("elapsed_ms"),"judged":len(judges),"pending":pending}


def _dash_render_full(data, width=92, ansi=False):
    """Full-height dashboard renderer."""
    snap = data.get("nodes") or {}
    local = snap.get("self") or {}
    health = data.get("health") or {}
    services = (data.get("services") or {}).get("services") or {}
    jobs = (data.get("jobs") or {}).get("jobs") or []
    http = data.get("http") or {}
    events = (data.get("events") or {}).get("events") or []
    pending_decisions = _dash_pending_decisions(data)
    # Leave one physical terminal column unused. Some emulators wrap/clobber the
    # final cell, which made the PULSE column appear chopped at the right edge.
    width = max(72, min(max(72, int(width or 92) - 1), 131))
    rule = "─" * width
    now_text = time.strftime("%Y-%m-%d %I:%M:%S %p %Z")
    peers = [p for p in (snap.get("peers") or []) if p.get("node")]
    live = 1 + sum(1 for p in peers if p.get("node"))

    lines = [f"FUTURE CRASH + LOOK · FABRIC DASH   {now_text}", rule]
    beacon = _active_beacon(events)
    if beacon:
        lines.append(f"FABRIC BEACON · {str(beacon['color']).upper()} · pulse {beacon['pulse']} · from {beacon.get('origin') or 'fabric'}")
        lines.append(rule)
    lines.append(f"FABRIC  {local.get('name','local')} · node {local.get('version','?')} · {local.get('release_name','')} · {live} node{'s' if live != 1 else ''}")

    warnings = []
    if not health.get("ok", False):
        warnings.append("local node health degraded")
    hm = ((http.get("listeners") or {}).get("local") or {})
    if int(hm.get("active") or 0) >= 16:
        warnings.append(f"HTTP active requests high ({hm.get('active')})")
    if int(hm.get("rejected") or 0):
        warnings.append(f"HTTP rejected {hm.get('rejected')}")
    if int(hm.get("accept_errors") or 0):
        warnings.append(f"HTTP accept errors {hm.get('accept_errors')}")
    for name, st in services.items():
        if st.get("managed") and st.get("state") not in {"active", "running"}:
            warnings.append(f"{name} {st.get('state','unknown')}")
    for peer in peers:
        node = peer.get("node") or {}
        if node.get("version") and node.get("version") != local.get("version"):
            warnings.append(f"version mismatch: {peer.get('name')} {node.get('version')}")
    if warnings:
        lines += ["", "WARNINGS", rule, " · ".join(warnings[:4])]

    node_w=23 if width>=104 else 20
    state_w=21 if width>=104 else 16
    model_w=max(24,width-node_w-state_w-11)
    lines += ["", "NODES", rule,
              f"{'NODE':<{node_w}} {'STATE':<{state_w}} {'MODEL':<{model_w}} {'PULSE':>8}"]
    rows = [(local.get("name") or "local", local, None)]
    rows += [(p.get("name") or "peer", p.get("node") or {}, p) for p in peers]
    for name, node, peer in rows:
        pulse = str((node.get("pulse") or {}).get("number", "—"))
        state = _dash_state(node)
        if peer and peer.get("node_seen_at"):
            age = _dash_age(now() - float(peer.get("node_seen_at") or now()))
            state = f"{state} · seen {age}"
        lines.append(f"{str(name):<{node_w}.{node_w}} {state:<{state_w}.{state_w}} {_dash_model(node):<{model_w}.{model_w}} {pulse:>8.8}")

    lines += ["", "CAPABILITIES", rule, _dash_capability_summary(data, width)]
    ds=_dash_decision_summary(data)
    decision_state="● ready" if ds["ready"] else "○ unavailable"
    last_bits=[]
    if ds.get("last"): last_bits.append(str(ds["last"]))
    if isinstance(ds.get("confidence"),(int,float)): last_bits.append(f"conf {ds['confidence']:.2f}")
    if isinstance(ds.get("margin"),(int,float)): last_bits.append(f"margin {ds['margin']:.2f}")
    if isinstance(ds.get("latency_ms"),(int,float)): last_bits.append(f"{ds['latency_ms']:.0f}ms")
    lines += ["", "COGNITION / DECISION", rule,
              f"rules ● ready   OpenJev 2B {decision_state}   pending {ds['pending']}   observed {ds['judged']}",
              "last · "+(" · ".join(last_bits) if last_bits else "no learned decision observed")]
    lines += ["", "TRUST BASIS", rule]
    clock = time.strftime("%Y-%m-%d %H:%M:%S %Z")
    caps = local.get("capabilities") or {}
    trust_bits = [f"clock ● {clock}",
                  f"filesystem {'● local' if caps.get('filesystem') else '○ unavailable'}",
                  f"fabric ● {live}/{live} advertising",
                  "provenance ● host-rendered receipts"]
    lines.append("   ".join(trust_bits))

    active_jobs = [j for j in jobs if str(j.get("status") or "") not in {"ok", "done", "failed", "cancelled", "canceled"}]
    lines += ["", "JOBS", rule]
    if active_jobs:
        for j in active_jobs[:5]:
            packet = j.get("packet") or {}
            op = packet.get("operation") or ((packet.get("work") or {}).get("operation")) or "?"
            lines.append(f"{str(j.get('id') or '?')[:12]:<12} {str(j.get('status') or '?'):<10.10} {str(op):<24.24} {str(j.get('worker') or '—'):<20.20}")
    else:
        lines.append("none active")

    if pending_decisions:
        lines += ["", f"HUMAN INPUT · {len(pending_decisions)} PENDING", rule]
        for decision in pending_decisions[:3]:
            lines.append(_dash_decision_line(decision,width))

    lines += ["", "CONTROL PLANE", rule]
    guard = (http.get("ingress_guard") or {}).get("ingress") or {}
    lines.append(
        f"local   conn {int(hm.get('connections_accepted', hm.get('accepted')) or 0):<6} "
        f"req {int(hm.get('requests_started') or 0):<6} done {int(hm.get('requests_completed', hm.get('completed')) or 0):<6} "
        f"active {int(hm.get('active') or 0):<3} rej {int(hm.get('rejected') or 0):<3} err {int(hm.get('errors') or 0):<3} "
        f"rate {float(hm.get('requests_per_sec_60s') or 0):.2f}/s"
    )
    if guard:
        lines.append(
            f"ingress conn {int(guard.get('connections_accepted', guard.get('accepted')) or 0):<6} "
            f"req {int(guard.get('requests_started') or 0):<6} done {int(guard.get('requests_completed', guard.get('completed')) or 0):<6} "
            f"active {int(guard.get('active') or 0):<3} rej {int(guard.get('rejected') or 0):<3} err {int(guard.get('errors') or 0):<3} "
            f"no-http {int(guard.get('connections_without_request') or 0):<4} early {int(guard.get('client_closed_early') or 0):<4} "
            f"rate {float(guard.get('requests_per_sec_60s') or 0):.2f}/s"
        )
        top = sorted((guard.get('by_endpoint') or {}).items(), key=lambda kv: kv[1], reverse=True)[:3]
        if top:
            lines.append("ingress top · " + "   ".join(f"{name} {count}" for name, count in top))

    lines += ["", "SERVICES", rule]
    if services:
        chunks = []
        for name, st in services.items():
            state = str(st.get("state") or "unknown")
            glyph = "●" if state in {"active", "running"} else ("·" if state == "unmanaged" else "○")
            chunks.append(f"{name} {glyph} {state}")
        lines.append("   ".join(chunks))
    else:
        lines.append("service status pending…")

    lines += ["", "RECENT · OBSERVED BY THIS NODE", rule]
    if events:
        for e in _dash_recent_events(events, 6):
            lines.append(_dash_recent_line(e, local.get("name"), width, ansi=ansi))
    else:
        lines.append("no recent Fabric events observed here")

    lines += ["", rule, _dash_controls(width)]
    return "\n".join(lines)


def _dash_summary_rows(data):
    """Dash consumes renderer-neutral node rows from the shared UI model."""
    ui=build_ui_model(data)
    return [(row.get("name") or "node", row.get("node") or {}) for row in (ui.get("nodes") or [])]


def _dash_render_compact(data, width=92, height=20, ansi=False):
    """Short-window dashboard: protect identity, workers, RECENT and controls."""
    width=max(30,min(int(width or 92),132)); rule="─"*width
    snap=data.get("nodes") or {}; local=snap.get("self") or {}; rows=_dash_summary_rows(data)
    events=(data.get("events") or {}).get("events") or []; jobs=(data.get("jobs") or {}).get("jobs") or []
    active=[j for j in jobs if str(j.get("status") or "") not in {"ok","done","failed","cancelled","canceled"}]
    pending_decisions=_dash_pending_decisions(data)
    lines=[f"FABRIC · {local.get('name','local')} · {len(rows)} node{'s' if len(rows)!=1 else ''} · {time.strftime('%H:%M:%S')}",rule]
    max_nodes=2 if height<18 else 3
    for name,node in rows[:max_nodes]:
        lines.append(f"{str(name):<20.20} {_dash_state(node):<13.13} {_dash_model(node)[:max(12,width-36)]}")
    if len(rows)>max_nodes:
        lines.append(f"+ {len(rows)-max_nodes} more node{'s' if len(rows)-max_nodes!=1 else ''}")
    http=data.get("http") or {}; hm=((http.get("listeners") or {}).get("local") or {})
    services=(data.get("services") or {}).get("services") or {}
    svc_ok=sum(1 for st in services.values() if str(st.get("state") or "") in {"active","running","unmanaged"})
    lines += [f"jobs {len(active)} · input {len(pending_decisions)} · ctl active {int(hm.get('active') or 0)} err {int(hm.get('errors') or 0)} · services {svc_ok}/{len(services) if services else 0}","RECENT",rule]
    # Reserve the footer and show as much recent activity as the rectangle allows.
    recent_slots=max(1,min(5,int(height)-len(lines)-2))
    if events:
        for e in _dash_recent_events(events, recent_slots): lines.append(_dash_recent_line(e,local.get("name"),width,ansi=ansi))
    else:
        lines.append("· no recent Fabric events")
    lines += [rule,_dash_controls(width)]
    return "\n".join(lines[-int(height):])


def _dash_service_bits(data):
    services=(data.get("services") or {}).get("services") or {}
    bits=[]
    for name,st in services.items():
        state=str(st.get("state") or "unknown")
        glyph="●" if state in {"active","running"} else ("·" if state=="unmanaged" else "○")
        bits.append(f"{name}{glyph}")
    return bits


def _dash_control_summary(data):
    http=data.get("http") or {}; hm=((http.get("listeners") or {}).get("local") or {})
    return (f"local {int(hm.get('requests_completed',hm.get('completed')) or 0)} done · "
            f"active {int(hm.get('active') or 0)} · err {int(hm.get('errors') or 0)}")


def _dash_ingress_summary(data):
    guard=(((data.get("http") or {}).get("ingress_guard") or {}).get("ingress") or {})
    if not guard:
        return "ingress —"
    return (f"ingress {int(guard.get('requests_completed',guard.get('completed')) or 0)} done · "
            f"active {int(guard.get('active') or 0)} · err {int(guard.get('errors') or 0)}")


def _dash_render_wide(data, width=120, height=28, ansi=False):
    """Information-dense landscape layout: spend horizontal pixels to save rows."""
    width=max(96,min(int(width or 120),196)); rule="─"*width
    snap=data.get("nodes") or {}; local=snap.get("self") or {}; rows=_dash_summary_rows(data)
    health=data.get("health") or {}; jobs=(data.get("jobs") or {}).get("jobs") or []
    events=(data.get("events") or {}).get("events") or []
    active=[j for j in jobs if str(j.get("status") or "") not in {"ok","done","failed","cancelled","canceled"}]
    pending_decisions=_dash_pending_decisions(data)
    services=" ".join(_dash_service_bits(data)) or "pending"
    caps=local.get("capabilities") or {}
    trust=(f"clock● fs{'●' if caps.get('filesystem') else '○'} "
           f"fabric {len(rows)}/{len(rows)} receipts●")

    lines=[f"FUTURE CRASH + LOOK · FABRIC DASH   {time.strftime('%Y-%m-%d %I:%M:%S %p %Z')}",rule,
           f"FABRIC  {local.get('name','local')} · node {local.get('version','?')} · {local.get('release_name','')} · {len(rows)} node{'s' if len(rows)!=1 else ''} · health {'ok' if health.get('ok') else 'degraded'}",
           "", "NODES / MODELS", rule]

    node_w=22 if width>=124 else 18
    state_w=15 if width>=124 else 12
    for name,node in rows:
        model_width=max(24,width-node_w-state_w-3)
        lines.append(f"{str(name):<{node_w}.{node_w}} {_dash_state(node):<{state_w}.{state_w}} {_dash_model(node)[:model_width]}")

    # Landscape terminals often have plenty of columns and very few rows.  Fold
    # secondary telemetry into two compact columns rather than throwing it away.
    lines += [""]
    gap="   │   "
    left_w=max(34,(width-len(gap))//2)
    right_w=max(30,width-len(gap)-left_w)
    ops=[
        (f"JOBS · {len(active)} active · INPUT {len(pending_decisions)}", f"TRUST · {trust}"),
        (f"CONTROL · {_dash_control_summary(data)}", f"SERVICES · {services}"),
        (f"{_dash_ingress_summary(data)}", f"CAPS · {_dash_capability_summary(data, right_w-7)}"),
    ]
    for left,right in ops:
        lines.append(f"{left[:left_w]:<{left_w}}{gap}{right[:right_w]}")

    lines += ["", "RECENT · OBSERVED BY THIS NODE", rule]
    # Fill the rectangle instead of using a fixed six-row ceiling.  RECENT is the
    # most useful spare-space consumer because every extra row carries real state.
    footer_rows=2
    recent_slots=max(2,int(height)-len(lines)-footer_rows)
    if events:
        for e in _dash_recent_events(events, recent_slots):
            lines.append(_dash_recent_line(e,local.get("name"),width,ansi=ansi))
    else:
        lines.append("· no recent Fabric events observed here")
    lines += [rule,_dash_controls(width)]
    return "\n".join(lines[:int(height)])


def _dash_render_condensed(data, width=92, height=30, ansi=False):
    """Medium rectangle: degrade detail gradually and use every available row."""
    width=max(64,min(int(width or 92),160)); rule="─"*width
    snap=data.get("nodes") or {}; local=snap.get("self") or {}; rows=_dash_summary_rows(data)
    health=data.get("health") or {}; jobs=(data.get("jobs") or {}).get("jobs") or []
    events=(data.get("events") or {}).get("events") or []
    active=[j for j in jobs if str(j.get("status") or "") not in {"ok","done","failed","cancelled","canceled"}]
    pending_decisions=_dash_pending_decisions(data)
    lines=[f"FUTURE CRASH + LOOK · FABRIC DASH   {time.strftime('%Y-%m-%d %I:%M:%S %p %Z')}",rule,
           f"FABRIC  {local.get('name','local')} · node {local.get('version','?')} · {local.get('release_name','')} · {len(rows)} node{'s' if len(rows)!=1 else ''} · health {'ok' if health.get('ok') else 'degraded'}","",
           "NODES / MODELS",rule]
    for name,node in rows:
        lines.append(f"{str(name):<22.22} {_dash_state(node):<14.14} {_dash_model(node)[:max(16,width-39)]}")

    services=" ".join(_dash_service_bits(data)) or "pending"
    # Add secondary evidence whenever the row budget permits.  This avoids the old
    # cliff where a 35-row terminal suddenly collapsed to a nearly-mini dashboard.
    reserve_recent=5
    reserve_footer=4
    spare=int(height)-len(lines)-reserve_recent-reserve_footer
    if spare>0:
        lines += [""]
        spare-=1
    if spare>0:
        lines.append(f"JOBS · {len(active)} active · INPUT {len(pending_decisions)}   CONTROL · {_dash_control_summary(data)}")
        spare-=1
    if spare>0:
        lines.append(f"SERVICES · {services}")
        spare-=1
    if spare>0:
        lines.append(f"TRUST · clock● · filesystem {'●' if (local.get('capabilities') or {}).get('filesystem') else '○'} · fabric {len(rows)}/{len(rows)} · receipts●")
        spare-=1
    if spare>0:
        lines.append(_dash_ingress_summary(data))
        spare-=1

    lines += ["","RECENT · OBSERVED BY THIS NODE",rule]
    recent_slots=max(2,int(height)-len(lines)-2)
    if events:
        for e in _dash_recent_events(events, recent_slots):
            lines.append(_dash_recent_line(e,local.get("name"),width,ansi=ansi))
    else:
        lines.append("· no recent Fabric events observed here")
    lines += [rule,_dash_controls(width)]
    return "\n".join(lines[:int(height)])


def _dash_render(data, width=92, height=None, ansi=False, mini=False):
    """Responsive renderer driven by information fit, not coarse height breakpoints."""
    if mini:
        return _dash_render_mini(data,width,ansi=ansi)
    if height is None:
        return _dash_render_full(data,width,ansi=ansi)
    width=max(1,int(width)); height=max(10,int(height))

    # First choice is always the richest renderer if it physically fits.
    full=_dash_render_full(data,width,ansi=ansi)
    if _dash_visual_rows(full,width) <= height:
        return full

    # Wide/short is its own geometry.  Use the width instead of punishing a
    # landscape Mac simply because it has fewer terminal rows than a portrait pane.
    if width < 64:
        return _dash_render_compact(data,width,height,ansi=ansi)
    if width >= 104 and height >= 19:
        return _dash_render_wide(data,width,height,ansi=ansi)
    if height >= 18:
        return _dash_render_condensed(data,width,height,ansi=ansi)
    return _dash_render_compact(data,width,height,ansi=ansi)

def _dash_fetch(host, port, cache, force=False):
    """Poll at deliberately different cadences so the dashboard never becomes load."""
    t = time.monotonic()
    schedule = {
        "nodes": ("/v1/nodes", 1.0),
        "health": ("/health", 2.0),
        "jobs": ("/v1/jobs", 2.0),
        "http": ("/v1/http", 2.0),
        "events": ("/v1/events", 0.5),
        "decisions": ("/v1/decisions/fabric", 2.0),
        "services": ("/v1/services", 8.0),
    }
    for key, (path, cadence) in schedule.items():
        due = float((cache.get("_next") or {}).get(key) or 0)
        if not force and t < due:
            continue
        try:
            cache[key] = _daemon_get(host, port, path)
            cache.setdefault("_errors", {}).pop(key, None)
        except Exception as exc:
            cache.setdefault("_errors", {})[key] = str(exc)
        cache.setdefault("_next", {})[key] = t + cadence
    return cache


def _dash_run_external(argv):
    """Run a sibling LOOK UI with the dashboard terminal restored."""
    exe = shutil.which("lk")
    if not exe:
        return
    subprocess.call([exe] + list(argv))


def _dash_restart_service(host, port):
    services = (_daemon_get(host, port, "/v1/services").get("services") or {})
    names = [name for name, st in services.items() if st.get("managed")]
    if not names:
        input("No Fabric-managed services on this node. Press Enter…")
        return
    print("\nManaged services: " + ", ".join(names))
    name = input("Restart service (blank cancels): ").strip()
    if not name:
        return
    if name not in names:
        input(f"Unknown/unmanaged service: {name}. Press Enter…")
        return
    answer = input(f"Restart {name} on local node? [y/N] ").strip().lower()
    if answer not in {"y", "yes"}:
        return
    result = _target_post(host, port, None, "/v1/services/action",
                          {"service": name, "action": "restart", "confirm": True})
    print(json.dumps(result, indent=2))
    input("Press Enter…")


def _dash_read_key(fd):
    """Read one dashboard command while swallowing terminal escape sequences.

    Arrow-down is ESC [ B; treating its final byte as a standalone `B` used to
    fire the beacon hotkey. Mouse wheel/drag reports have the same shape.
    """
    ch = sys.stdin.read(1)
    if ch != "\x1b":
        return ch
    # Drain the rest of a CSI/SS3/mouse report without dispatching any byte as a
    # command. The short quiet timeout keeps a lone Escape harmless and cheap.
    deadline = time.monotonic() + 0.03
    while time.monotonic() < deadline:
        ready, _, _ = select.select([sys.stdin], [], [], 0.003)
        if not ready:
            break
        part = sys.stdin.read(1)
        if not part:
            break
        # ANSI CSI final bytes live in 0x40..0x7e. Mouse SGR reports may include
        # parameters first, but end in M/m. Once final arrives the report is done.
        if "@" <= part <= "~":
            break
    return None


def _dashboard(host, port, interval=0.25):
    cache = {"_next": {}, "_errors": {}}
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        _dash_fetch(host, port, cache, force=True)
        print(_dash_render(cache, shutil.get_terminal_size((92, 30)).columns))
        return 0

    import termios
    import tty
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    alt = "\033[?1049h\033[?25l"
    normal = "\033[0m\033[?25h\033[?1049l"

    def raw_on():
        tty.setcbreak(fd)
        sys.stdout.write(alt)
        sys.stdout.flush()

    def raw_off():
        try:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)
        finally:
            sys.stdout.write(normal)
            sys.stdout.flush()

    raw_on()
    try:
        dirty = True
        mini = False
        activity_flash = None
        activity_flash_until = 0.0
        last_event_seq = None
        last_draw = 0.0
        last_beacon_hotkey = 0.0
        while True:
            _dash_fetch(host, port, cache, force=dirty)
            observed = ((cache.get("events") or {}).get("events") or [])
            newest_seq = int((observed[-1] or {}).get("seq") or 0) if observed else 0
            if last_event_seq is None:
                # Opening Dash should not replay yesterday's activity as a flash.
                last_event_seq = newest_seq
            elif newest_seq > last_event_seq:
                fresh = [e for e in observed if int(e.get("seq") or 0) > last_event_seq]
                last_event_seq = newest_seq
                for event in reversed(fresh):
                    if not _dash_event_visible(event):
                        continue
                    color = _dash_event_flash(event)
                    if color:
                        activity_flash = color
                        activity_flash_until = time.monotonic() + 0.38
                        dirty = True
                        break
            t = time.monotonic()
            if activity_flash and t >= activity_flash_until:
                activity_flash = None
                dirty = True
            if dirty or t - last_draw >= 1.0:
                size = shutil.get_terminal_size((92, 30))
                body = _dash_render(cache, size.columns, height=size.lines, ansi=True, mini=mini)
                beacon = _active_beacon(((cache.get("events") or {}).get("events") or []))
                beacon_bg = {"red":"41;97", "green":"42;30", "blue":"44;97", "white":"47;30"}.get((beacon or {}).get("color"))
                bg = beacon_bg or activity_flash
                prefix = (f"\033[{bg}m" if bg else "\033[0m") + "\033[2J\033[H"
                sys.stdout.write(prefix + body)
                errors = cache.get("_errors") or {}
                if errors:
                    sys.stdout.write("\n" + " · ".join(f"{k}: {v}" for k, v in list(errors.items())[:2]))
                sys.stdout.flush()
                last_draw = t
                dirty = False
            ready, _, _ = select.select([sys.stdin], [], [], interval)
            if not ready:
                continue
            ch = _dash_read_key(fd)
            if ch is None:
                continue
            if ch in {"q", "Q", "\x03"}:
                return 0
            if ch == " ":
                dirty = True
            elif ch in {"m", "M"}:
                mini = not mini
                dirty = True
            elif ch in {"b", "B"}:
                # One physical keypress -> one beacon. Ignore key-repeat/garbage
                # while the previous diagnostic animation is still in flight.
                stamp = time.monotonic()
                if stamp - last_beacon_hotkey < 2.0:
                    continue
                last_beacon_hotkey = stamp
                try:
                    http_json(_daemon_url(host, port, "/v1/beacon"),
                              {"pattern":"rgb", "lead_pulses":3}, timeout=3.0)
                finally:
                    dirty = True
            elif ch in {"l", "L"}:
                try:
                    http_json(_daemon_url(host, port, "/v1/lights"),
                              {"pattern":"demo"}, timeout=3.0)
                finally:
                    dirty = True
            elif ch in {"w", "W"}:
                raw_off()
                try:
                    _watch(host, port)
                finally:
                    raw_on(); dirty = True
            elif ch in {"s", "S"}:
                raw_off()
                try:
                    _dash_run_external(["settings"])
                finally:
                    raw_on(); dirty = True
            elif ch in {"d", "D"}:
                raw_off()
                try:
                    _dash_run_external(["doctor"])
                    input("Press Enter to return to dashboard…")
                finally:
                    raw_on(); dirty = True
            elif ch in {"r", "R"}:
                raw_off()
                try:
                    _dash_restart_service(host, port)
                finally:
                    raw_on(); dirty = True
    except KeyboardInterrupt:
        return 0
    finally:
        raw_off()


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
        choices=["serve","status","nodes","activity","pulse","fabric","watch","dashboard","models","qualify","services","service",
                 "jobs","job","submit","packet","cancel","events","http","beacon","lights","artifact-add","artifact","artifacts","file-catalog","file-find","media-catalog","media-identify",
                 "decisions","decision","answer","ask","decision-shadow","decision-provider","identity","trust","untrust","pair-code","pair","transport","endpoints","endpoint-code","allow","revoke-endpoint","media-outputs","media-state","media-play","media-control"])
    ap.add_argument("args",nargs="*")
    ap.add_argument("--node",dest="node",default=None,help="target Fabric node name")
    ap.add_argument("--json",action="store_true",help="raw JSON where a human view exists")
    ap.add_argument("--yes",action="store_true",help="confirm a mutating managed-service action")
    ap.add_argument("--host",default=DEFAULT_HOST); ap.add_argument("--port",type=int,default=DEFAULT_PORT)
    ap.add_argument("--ingress-port",type=int,default=DEFAULT_INGRESS_PORT,
                    help="legacy in-process ingress listener; 0 disables (default; use fcl-ingress)")
    ap.add_argument("--version",action="version",version=f"Future Crash + LOOK node {VERSION} · {RELEASE_NAME}")
    ap.add_argument("--version-number",action="version",version=VERSION)
    a=ap.parse_args()
    if a.command != "serve":
        try:
            if a.command=="watch": return _watch(a.host,a.port)
            if a.command=="dashboard": return _dashboard(a.host,a.port)
            if a.command=="beacon":
                pattern = a.args[0] if a.args else "rgb"
                result = http_json(_daemon_url(a.host,a.port,"/v1/beacon"), {"pattern": pattern, "lead_pulses": 3}, timeout=3.0)
                print(f"FABRIC BEACON · {result.get('pattern','rgb')} · pulse {result.get('start_pulse','?')} · {result.get('delivered',0)}/{result.get('expected',0)} nodes")
                for row in result.get("delivery") or []:
                    mark = "✓" if row.get("ok") else "×"
                    detail = f"received pulse {row.get('received_pulse')}" if row.get("ok") else str(row.get("error") or "failed")
                    print(f"  {mark} {str(row.get('node') or '?'):<24} {detail}")
                return 0 if result.get("ok") else 1
            if a.command=="lights":
                pattern = a.args[0] if a.args else "demo"
                if pattern == "stop":
                    result = http_json(_daemon_url(a.host,a.port,"/v1/lights"), {"pattern":"pulse","show_id":"*","start_pulse":pulse_number(),"stopped":True}, timeout=3.0)
                    print("FABRIC LIGHTS · stopped")
                    return 0
                if pattern not in BEACON_PATTERNS:
                    ap.error("lights pattern must be demo|rgb|pulse|christmas|disco|stop")
                repeating = pattern in {"christmas","disco"}
                if not repeating:
                    result = http_json(_daemon_url(a.host,a.port,"/v1/lights"), {"pattern":pattern}, timeout=3.0)
                    print(f"FABRIC LIGHTS · {pattern} · pulse {result.get('start_pulse','?')} · {result.get('delivered',0)}/{result.get('expected',0)} nodes")
                    return 0 if result.get("ok") else 1
                show_id = uuid.uuid4().hex[:12]
                start_pulse = pulse_number() + 3
                print(f"FABRIC LIGHTS · {pattern} · Ctrl-C stops · show {show_id}")
                try:
                    while True:
                        result = http_json(_daemon_url(a.host,a.port,"/v1/lights"), {
                            "pattern":pattern,"show_id":show_id,"start_pulse":start_pulse,
                            "repeat":True,"lease_pulses":8}, timeout=3.0)
                        time.sleep(5.0)
                except KeyboardInterrupt:
                    try:
                        http_json(_daemon_url(a.host,a.port,"/v1/lights"), {
                            "pattern":pattern,"show_id":show_id,"start_pulse":start_pulse,
                            "stopped":True}, timeout=2.0)
                    except Exception:
                        pass
                    print("\nFABRIC LIGHTS · stopped")
                    return 0
            if a.command=="fabric": print_fabric_snapshot(_daemon_get(a.host,a.port,"/v1/nodes")); return 0
            if a.command=="nodes": print(json.dumps(_daemon_get(a.host,a.port,"/v1/nodes"),indent=2)); return 0
            if a.command=="identity":
                me=FABRIC_IDENTITY.ensure(); live=identity()
                me["name"]=live.get("name") or me.get("name"); me["hostname"]=live.get("hostname") or me.get("hostname")
                if a.json: print(json.dumps(me,indent=2))
                else:
                    print(f"FABRIC IDENTITY · {me['name']}")
                    print(f"  node id      {me['node_id']}")
                    print(f"  fingerprint  {me['fingerprint']}")
                    print("  key          ssh-ed25519 · local private key never leaves this machine")
                return 0
            if a.command=="trust":
                data=FABRIC_IDENTITY.trusted(public=True); rows=list((data.get("nodes") or {}).values())
                if a.json: print(json.dumps(data,indent=2)); return 0
                print(f"FABRIC TRUST · {len(rows)} node{'s' if len(rows)!=1 else ''}")
                for row in sorted(rows,key=lambda x:(str(x.get('name') or ''),str(x.get('node_id') or ''))):
                    print(f"  {str(row.get('name') or '?'):<20.20} {row.get('node_id','')}  {row.get('fingerprint','')}  {'AUTH' if row.get('authorized') else 'RE-PAIR'}")
                return 0
            if a.command=="untrust":
                if not a.args: ap.error("untrust requires NODE_ID")
                ok=FABRIC_IDENTITY.untrust(a.args[0]); print("FABRIC TRUST · removed" if ok else "FABRIC TRUST · node not found")
                return 0 if ok else 1
            if a.command=="pair-code":
                ts=tailscale_self(); supplied=a.args[0] if a.args else ""
                endpoint=supplied.rstrip("/") if supplied else (f"https://{ts.get('dns')}:7332" if ts.get('dns') else "")
                if not endpoint:
                    ap.error("pair-code needs an endpoint URL when no reachable address can be inferred")
                invite=FABRIC_IDENTITY.start_pairing(endpoint,name=identity().get("name") or "",hostname=socket.gethostname())
                if a.json: print(json.dumps(invite,indent=2)); return 0
                short=(ts.get("dns") or "").split(".",1)[0] or invite['identity']['name']
                print(f"FABRIC PAIR · {invite['identity']['name']} · invitation open for 5 minutes")
                print(f"  code  {invite['code']}")
                print(f"  on the other node:  lk fabric pair {short} {invite['code']}")
                print(f"  endpoint            {invite['endpoint']}")
                qr=shutil.which("qrencode")
                if qr and sys.stdout.isatty():
                    print("  scan instead:")
                    try: subprocess.run([qr,"-t","ANSIUTF8",f"FCL PAIR\n{short}\n{invite['code']}\n{invite['endpoint']}"],timeout=2,check=False)
                    except Exception: pass
                return 0
            if a.command=="pair":
                if not a.args: ap.error("pair requires NODE CODE, ENDPOINT CODE, or an fcl://pair URI")
                target=a.args[0]; code=a.args[1] if len(a.args)>1 else None
                if not target.startswith(("http://","https://","fcl://")):
                    wanted=target.casefold(); hit=None
                    for row in peer_rows():
                        names={str(row.get("name") or "").casefold(),str(row.get("dns") or "").casefold(),str(row.get("dns") or "").split(".",1)[0].casefold()}
                        if wanted in names and row.get("dns"): hit=row; break
                    if not hit: ap.error(f"cannot resolve Fabric peer {target!r}; use its endpoint URL")
                    target=f"https://{hit['dns']}:7332"
                ts=tailscale_self(); local_endpoint=(f"https://{ts.get('dns')}:7332" if ts.get('dns') else None)
                result=join_pairing(FABRIC_IDENTITY,target,code,name=identity().get("name") or "",hostname=socket.gethostname(),local_endpoint=local_endpoint)
                peer=result["peer"]
                print(f"FABRIC PAIR · trusted {peer.get('name') or peer.get('node_id')} · {peer.get('fingerprint')}")
                return 0
            if a.command=="transport":
                snap=_daemon_get(a.host,a.port,"/v1/nodes")
                tc=(FABRIC_IDENTITY.local_transports().get("tailcat") or {})
                if a.json:
                    print(json.dumps({"tailcat":tc,"peers":snap.get("peers") or []},indent=2)); return 0
                print("FABRIC TRANSPORT")
                if tc.get("endpoints"):
                    print("  local  TAILCAT  "+", ".join(tc.get("endpoints") or []))
                else:
                    print("  local  TAILCAT  unavailable")
                for peer in snap.get("peers") or []:
                    if not peer.get("node"): continue
                    active=str(peer.get("active_transport") or ("tailscale" if peer.get("dns") else "unreachable")).upper()
                    if active=="TAILSCALE" and not peer.get("trusted"):
                        active="TAILSCALE*"
                    base=_peer_base(peer) or "—"
                    print(f"  {str(peer.get('name') or '?'):<18} {active:<10} {base}")
                print("  policy  Tailcat direct TLS first · Tailscale fallback")
                print("          * TAILSCALE* = discovered transport only; peer is not directly paired/trusted")
                return 0
            if a.command=="endpoints":
                data=_daemon_get(a.host,a.port,"/v1/endpoints/fabric")
                if a.json: print(json.dumps(data,indent=2)); return 0
                totals={"trusted":0,"sessions":0,"pending":0}
                for node in data.get("nodes") or []:
                    for key in totals: totals[key]+=len(node.get(key) or [])
                print(f"FABRIC ENDPOINTS · {totals['trusted']} trusted · {totals['sessions']} temporary · {totals['pending']} pending")
                for node in data.get("nodes") or []:
                    rows=sum((len(node.get(k) or []) for k in ("pending","trusted","sessions")),0)
                    if not rows: continue
                    print(f"  {str(node.get('node') or 'local')}:")
                    for row in node.get('pending') or []:
                        print(f"    PENDING  {row.get('code')}  {str(row.get('user_agent') or 'browser')[:54]}")
                    for row in node.get('trusted') or []:
                        print(f"    TRUSTED  {row.get('endpoint_id')}  {row.get('label') or 'Browser'}")
                    for row in node.get('sessions') or []:
                        print(f"    ONCE     {row.get('endpoint_id')}  {row.get('label') or 'Browser'}")
                for err in data.get("errors") or []:
                    print(f"  ! {err.get('node')} · {err.get('error')}")
                return 0
            if a.command=="allow":
                if not a.args: ap.error("allow requires the six-digit endpoint code [once|trust]")
                mode=a.args[1] if len(a.args)>1 else "once"
                try:
                    result=_daemon_post(a.host,a.port,"/v1/endpoints/fabric/allow",{"code":a.args[0],"mode":mode})
                except RuntimeError as exc:
                    # A 6.1.0 install could leave an older resident node answering
                    # localhost briefly. Route from the CLI rather than making the
                    # human discover which node owns the browser code.
                    if "404" not in str(exc): raise
                    result=_endpoint_allow_cli_fallback(a.host,a.port,a.args[0],mode)
                row=result.get("endpoint") or {}
                print(f"FABRIC ENDPOINT · {row.get('code') or a.args[0]} approved on {result.get('node')} · {mode}")
                return 0
            if a.command=="revoke-endpoint":
                if not a.args: ap.error("revoke-endpoint requires ENDPOINT_ID")
                try:
                    result=_daemon_post(a.host,a.port,"/v1/endpoints/fabric/revoke",{"endpoint_id":a.args[0]})
                except RuntimeError as exc:
                    print(f"FABRIC ENDPOINT · {exc}"); return 1
                if result.get("ok"):
                    print(f"FABRIC ENDPOINT · revoked on {result.get('node')}"); return 0
                print(f"FABRIC ENDPOINT · {result.get('error') or 'not found'}"); return 1
            if a.command=="endpoint-code":
                ts=tailscale_self(); supplied=a.args[0] if a.args else os.getenv("FCL_SIGNAL_URL","")
                url=supplied.rstrip("/") if supplied else (f"https://{ts.get('dns')}:7331" if ts.get('dns') else "")
                mode=a.args[1] if len(a.args)>1 else "trust"
                if not url: ap.error("endpoint-code needs the externally reachable Signal URL")
                invite=ENDPOINT_AUTH.create_invite(url,mode=mode)
                if a.json: print(json.dumps(invite,indent=2)); return 0
                print(f"FABRIC ENDPOINT · {mode} invitation · expires in 5 minutes")
                print(f"  URL  {invite['url']}")
                qr=shutil.which("qrencode")
                if qr and sys.stdout.isatty():
                    print("  scan with iPhone camera:")
                    try: subprocess.run([qr,"-t","ANSIUTF8",invite["url"]],timeout=2,check=False)
                    except Exception: pass
                return 0
            path={"status":"/v1/node","activity":"/v1/activity","pulse":"/v1/pulse","models":"/v1/models","services":"/v1/services","http":"/v1/http"}.get(a.command)
            if path:
                data=_target_get(a.host,a.port,a.node,path)
                if a.command=="models" and not a.json: _print_models(data,a.node or "local")
                else: print(json.dumps(data,indent=2))
                return 0
            if a.command=="media-outputs":
                payload = _daemon_get(a.host, a.port, "/v1/media/outputs")
                if a.json:
                    print(json.dumps(payload, indent=2))
                else:
                    print(f"FABRIC MEDIA OUTPUTS · {int(payload.get('count') or 0)}")
                    for row in payload.get("outputs") or []:
                        mark="●" if row.get("available") else "○"
                        active=" · "+str(row.get("state") or "") if row.get("active") else ""
                        print(f"  {mark} {str(row.get('node') or '?'):<20} {str(row.get('output_id') or 'default')}{active}")
                return 0
            if a.command=="media-state":
                payload = _target_get(a.host, a.port, a.node, "/v1/media/state") if a.node else _daemon_get(a.host, a.port, "/v1/media/state")
                print(json.dumps(payload, indent=2) if a.json else json.dumps(payload, ensure_ascii=False))
                return 0
            if a.command=="media-play":
                if not a.args: ap.error("media-play requires QUERY")
                payload = _daemon_post(a.host, a.port, "/v1/media/route", {"node":a.node or "","operation":"play","query":" ".join(a.args)})
                print(json.dumps(payload, indent=2) if a.json else (payload.get("message") or f"MEDIA PLAY · {payload.get('node') or a.node or 'local'}"))
                return 0
            if a.command=="media-control":
                if not a.args: ap.error("media-control requires ACTION")
                payload={"node":a.node or "","operation":"control","action":a.args[0]}
                if a.args[0]=="jump" and len(a.args)>1:
                    payload["index"]=max(0,int(a.args[1])-1)
                result=_daemon_post(a.host,a.port,"/v1/media/route",payload)
                print(json.dumps(result, indent=2) if a.json else (result.get("message") or f"MEDIA {a.args[0]} · {result.get('node') or a.node or 'local'}"))
                return 0
            if a.command=="file-find":
                if not a.args: ap.error("file-find requires QUERY")
                query=" ".join(a.args); payload=_daemon_get(a.host,a.port,"/v1/files/find?q="+urllib.parse.quote(query))
                if a.json: print(json.dumps(payload,indent=2))
                else:
                    print(f"FABRIC FIND · {int(payload.get('count') or 0)} · {query}")
                    for row in payload.get("entries") or []: print(f"  {str(row.get('node') or '?'):<18} {row.get('path') or '?'}")
                return 0
            if a.command=="file-catalog":
                payload = _target_get(a.host,a.port,a.node,"/v1/files/catalog") if a.node else _daemon_get(a.host,a.port,"/v1/files/fabric")
                if a.json: print(json.dumps(payload,indent=2))
                else:
                    print(f"FABRIC FILES · {int(payload.get('locations',payload.get('count',0))):,} cataloged locations")
                    for row in payload.get("nodes") or []: print(f"  {str(row.get('node') or '?'):<20} {int(row.get('count') or 0):>9,} files")
                return 0
            if a.command=="media-catalog":
                payload = _target_get(a.host, a.port, a.node, "/v1/media/catalog") if a.node else _daemon_get(a.host, a.port, "/v1/media/fabric")
                if a.json:
                    print(json.dumps(payload, indent=2))
                else:
                    print(f"FABRIC MEDIA · {payload.get('locations', payload.get('count',0)):,} scanned locations · {payload.get('identified_locations', payload.get('identified',0)):,} identified")
                    for row in payload.get("nodes") or []:
                        print(f"  {str(row.get('node') or '?'):<20} {int(row.get('count') or 0):>6,} scanned · {int(row.get('identified') or 0):>6,} SHA")
                return 0
            if a.command=="media-identify":
                if not a.args: ap.error("media-identify requires ENTRY_ID")
                result = _target_post(a.host, a.port, a.node, "/v1/media/identify", {"id": a.args[0]}, timeout=600.0)
                if a.json:
                    print(json.dumps(result, indent=2))
                else:
                    entry=result.get("entry") or {}
                    print(f"FABRIC MEDIA · identified {entry.get('artist') or ''} {entry.get('title') or entry.get('id') or ''}".strip())
                    print(f"  {(result.get('artifact') or {}).get('digest','?')}")
                return 0
            if a.command=="artifacts":
                payload = _daemon_get(a.host, a.port, "/v1/artifacts/fabric") if not a.node else _target_get(a.host, a.port, a.node, "/v1/artifacts")
                if a.json:
                    print(json.dumps(payload, indent=2))
                else:
                    print(f"FABRIC ARTIFACTS · {int(payload.get('count') or 0):,}")
                    for row in (payload.get("artifacts") or [])[:80]:
                        print(f"  {str(row.get('digest') or '')[:20]:<20}  {str(row.get('media_type') or ''):<22}  {row.get('name') or '?'}")
                return 0
            if a.command=="artifact-add":
                if not a.args: ap.error("artifact-add requires PATH")
                try:
                    meta = ARTIFACTS.register_file(a.args[0])
                except (OSError, ValueError) as exc:
                    print(f"FCL ARTIFACT · {exc}", file=sys.stderr)
                    return 1
                try:
                    FABRIC_STORE.event(None, "artifact", "registered", meta.get("name") or meta["digest"],
                                       node=identity()["name"], data={"digest":meta["digest"],"bytes":meta.get("bytes"),"media_type":meta.get("media_type")})
                except Exception:
                    pass
                payload = {"artifact": _artifact_public_metadata(meta),
                           "stream_url": _artifact_target_url(a.host, a.port, None, meta["digest"])}
                if a.json:
                    print(json.dumps(payload, indent=2))
                else:
                    print(f"FABRIC ARTIFACT · {meta.get('name') or Path(a.args[0]).name}")
                    print(f"  {meta['digest']} · {meta.get('bytes',0)} bytes · file-backed")
                    print(f"  {payload['stream_url']}")
                return 0
            if a.command=="artifact":
                if not a.args: ap.error("artifact requires DIGEST")
                digest = a.args[0]
                url = _artifact_target_url(a.host, a.port, a.node, digest)
                meta = http_json(url + "?meta=1", timeout=4.0).get("artifact") or {}
                payload = {"artifact": meta, "stream_url": url, "node": a.node or "local"}
                if a.json:
                    print(json.dumps(payload, indent=2))
                else:
                    print(f"FABRIC ARTIFACT · {meta.get('name') or digest}")
                    print(f"  {digest} · {meta.get('bytes','?')} bytes · {meta.get('media_type','application/octet-stream')}")
                    print(f"  {url}")
                return 0
            if a.command=="decision-provider":
                data=_target_get(a.host,a.port,a.node,"/v1/decisions/provider") if a.node else _daemon_get(a.host,a.port,"/v1/decisions/provider")
                if a.json:
                    print(json.dumps(data,indent=2)); return 0
                print("FABRIC DECISION WORKER")
                print("─"*64)
                print(f"  provider    {data.get('provider','?')}")
                print(f"  state       {data.get('state','?')}")
                print(f"  mode        {data.get('mode','?')}")
                print(f"  endpoint    {data.get('url','?')}")
                if data.get('latency_ms') is not None: print(f"  latency     {float(data['latency_ms']):.0f} ms")
                if data.get('last_error'): print(f"  last error  {data.get('last_error')}")
                return 0
            if a.command=="decisions":
                data=_target_get(a.host,a.port,a.node,"/v1/decisions") if a.node else _daemon_get(a.host,a.port,"/v1/decisions/fabric")
                if a.json:
                    print(json.dumps(data,indent=2)); return 0
                rows=data.get("decisions") or []
                print(f"FABRIC DECISIONS · {len(rows)} pending")
                print("─"*96)
                now_ts=now()
                for row in rows:
                    left=max(0,int(float(row.get("expires") or now_ts)-now_ts))
                    print(f"  {str(row.get('id') or '?'):<42.42} {str(row.get('node') or a.node or 'local'):<16.16} {left:>3}s  {str(row.get('question') or '')[:30]}")
                return 0
            if a.command=="decision":
                if not a.args: ap.error("decision requires ID")
                print(json.dumps(_target_get(a.host,a.port,a.node,f"/v1/decisions/{a.args[0]}"),indent=2)); return 0
            if a.command=="answer":
                if len(a.args)<2: ap.error("answer requires DECISION_ID CHOICE")
                result=_target_post(a.host,a.port,None,"/v1/decisions/answer",{
                    "node":a.node,"id":a.args[0],"selected":a.args[1],"source":"terminal"},timeout=5.0)
                print(json.dumps(result,indent=2) if a.json else f"FABRIC DECISION · {a.args[0]} → {a.args[1]}")
                return 0
            if a.command=="ask":
                if not a.args: ap.error("ask requires QUESTION [CHOICE ...]")
                question=a.args[0]; labels=a.args[1:] or ["yes","no"]
                payload={
                    "question":question,
                    "choices":[{"value":str(x),"label":str(x)} for x in labels],
                    "profile":os.environ.get("FCL_ACCESS_PROFILE","workspace"),
                    "confidence":0.5,"consequence":"low","reversible":True,
                    "shadow_openjev":str(os.environ.get("FCL_DECISION_SHADOW") or "").lower() in {"1","true","yes","on"},
                }
                result=_target_post(a.host,a.port,a.node,"/v1/decisions",payload,timeout=4.0)
                d=result.get("decision") or {}
                if a.json:
                    print(json.dumps(result,indent=2)); return 0
                did=str(d.get("id") or "")
                print(f"FABRIC ASK · {did or '?'} · {d.get('question','')} · {int(max(0,float(d.get('expires') or now())-now()))}s")
                # A terminal is one consumer of a Fabric decision, not its owner.
                # Poll while stdin is idle so Signal/Dash can answer the same request
                # and release this terminal immediately rather than making ASK block.
                if not (did and sys.stdin.isatty() and sys.stdout.isatty()):
                    return 0
                import select
                choices=[str(x.get("value")) for x in (d.get("choices") or []) if isinstance(x,dict)]
                prompt=" / ".join(choices)
                print(f"  [{prompt}]  Enter leaves it pending for Signal/Fabric")
                sys.stdout.write("  > "); sys.stdout.flush()
                expires=float(d.get("expires") or now())
                while now() < expires:
                    current=(_target_get(a.host,a.port,a.node,f"/v1/decisions/{did}").get("decision") or {})
                    if current.get("status") != "pending":
                        sys.stdout.write("\r\033[2K")
                        print(f"FABRIC DECISION · {did} → {current.get('selected') or current.get('status')} · {current.get('response_source') or 'timeout'}")
                        return 0
                    ready,_,_=select.select([sys.stdin],[],[],0.25)
                    if not ready:
                        continue
                    entered=sys.stdin.readline().strip()
                    if not entered:
                        print(f"FABRIC ASK · pending · answer anywhere with decision {did}")
                        return 0
                    folded=entered.casefold()
                    selected=next((x for x in choices if x.casefold()==folded),None)
                    if selected is None and entered.isdigit() and 1 <= int(entered) <= len(choices):
                        selected=choices[int(entered)-1]
                    if selected is None:
                        print(f"  choose {' / '.join(choices)} (or number); Enter leaves pending")
                        sys.stdout.write("  > "); sys.stdout.flush(); continue
                    answered=_target_post(a.host,a.port,None,"/v1/decisions/answer",{
                        "node":a.node,"id":did,"selected":selected,"source":"terminal"},timeout=5.0)
                    resolved=answered.get("decision") or current
                    print(f"FABRIC DECISION · {did} → {resolved.get('selected') or selected}")
                    return 0
                final=(_target_get(a.host,a.port,a.node,f"/v1/decisions/{did}").get("decision") or {})
                print(f"FABRIC DECISION · {did} → {final.get('selected') or final.get('status') or 'timed out'}")
                return 0
            if a.command=="decision-shadow":
                if len(a.args)<3: ap.error("decision-shadow requires STATE QUESTION CANDIDATE...")
                result=_target_post(a.host,a.port,a.node,"/v1/decisions/shadow",{
                    "state":a.args[0],"question":a.args[1],"candidates":a.args[2:]},timeout=4.0)
                print(json.dumps(result,indent=2)); return 0
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
    faulthandler.enable(all_threads=True)
    if hasattr(signal, "SIGUSR1"):
        faulthandler.register(signal.SIGUSR1, file=sys.stderr, all_threads=True)
    threading.Thread(target=pulse_loop,name="fabric-pulse",daemon=True).start()
    threading.Thread(target=background_qualifier,name="model-qualifier",daemon=True).start()
    threading.Thread(target=background_curator,name="model-curator",daemon=True).start()
    threading.Thread(target=job_worker_loop,name="fabric-jobs",daemon=True).start()
    threading.Thread(target=_decision_expiry_loop,name="fabric-decisions",daemon=True).start()
    JOB_WAKE.set()
    srv=FabricHTTPServer((a.host,a.port),API,plane="local")
    threading.Thread(target=_local_accept_watchdog,args=(srv,),name="fabric-http-watchdog",daemon=True).start()
    ingress=None
    ingress_thread=None
    if a.ingress_port and int(a.ingress_port) != int(a.port):
        ingress=FabricHTTPServer((a.host,int(a.ingress_port)),API,plane="ingress")
        ingress_thread=threading.Thread(target=ingress.serve_forever,kwargs={"poll_interval":.2},
                                        name="fabric-ingress",daemon=True)
        ingress_thread.start()
    ingress_note=f" · ingress {a.host}:{a.ingress_port}" if ingress else ""
    print(f"Future Crash + LOOK node {VERSION} · {RELEASE_NAME} · local http://{a.host}:{a.port}{ingress_note} · pulse {PULSE_SECONDS:g}s",flush=True)
    try: srv.serve_forever(poll_interval=.2)
    except KeyboardInterrupt: pass
    finally:
        srv.server_close()
        if ingress:
            ingress.shutdown(); ingress.server_close()
    return 0


if __name__ == "__main__":
    main()
