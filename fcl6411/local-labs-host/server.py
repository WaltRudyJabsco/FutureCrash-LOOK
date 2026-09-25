#!/usr/bin/env python3
"""
Local Labs Host Controller v0.6.0

Milestone 2 — observe + operate known services:
  server status
  server discover
  server status <service>
  server start|stop|restart <service>
  server logs <service>

Linux remains the source of truth. This program observes it; it does not
supervise processes or silently repair configuration.
"""
from __future__ import annotations

import json
import os
import platform
import re
import signal
import time
import shutil
import socket
import subprocess
import sys
import urllib.request
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional


VERSION = "0.6.0"
HOME = Path.home()


@dataclass(frozen=True)
class ServiceSpec:
    id: str
    name: str
    port: Optional[int] = None
    system_unit: Optional[str] = None
    user_unit: Optional[str] = None
    process_patterns: tuple[str, ...] = ()
    install_paths: tuple[str, ...] = ()
    health_path: str = "/"
    gpu: bool = False


SERVICES = (
    ServiceSpec(
        id="ollama",
        name="Ollama",
        port=11434,
        system_unit="ollama.service",
        process_patterns=("ollama serve",),
        install_paths=("/usr/local/bin/ollama", "/home/linuxbrew/.linuxbrew/bin/ollama"),
        health_path="/api/version",
        gpu=True,
    ),
    ServiceSpec(
        id="comfy",
        name="ComfyUI",
        port=8188,
        user_unit="server-comfy.service",
        process_patterns=("ComfyUI", "main.py --listen 127.0.0.1 --port 8188"),
        install_paths=("~/.local/share/look/services/comfyui/ComfyUI",),
        health_path="/system_stats",
        gpu=True,
    ),
    ServiceSpec(
        id="mercury",
        name="Mercury Writer",
        port=8765,
        user_unit="server-mercury.service",
        process_patterns=("mercury_server.py",),
        install_paths=("~/.local/share/mercury-writer",),
    ),
    ServiceSpec(
        id="searxng",
        name="SearXNG",
        port=8888,
        system_unit="server-searxng.service",
        process_patterns=("/usr/bin/uwsgi", "searx.webapp"),
        install_paths=("/usr/local/searxng/searxng-src", "/etc/searxng/settings.yml"),
        health_path="/",
    ),
    ServiceSpec(
        id="openjev",
        name="OpenJev Decision",
        port=8791,
        user_unit="future-crash-look-openjev.service",
        process_patterns=("jev.server", "Open-Jev"),
        install_paths=("~/.local/share/open-jev", "~/.config/systemd/user/future-crash-look-openjev.service"),
        health_path="/",
        gpu=True,
    ),
    ServiceSpec(
        id="signal",
        name="Signal Window",
        port=7331,
        user_unit="signal-window.service",
        process_patterns=("signal-window/server.py", ".local/share/signal-window/server.py"),
        install_paths=("~/.local/share/signal-window/server.py",),
        health_path="/api/status",
    ),
    ServiceSpec(
        id="console",
        name="Operator Console",
        port=3090,
        user_unit="server-console.service",
        process_patterns=("3090-server/console.py",),
        install_paths=("~/.local/share/3090-server/console.py",),
        health_path="/",
    ),
    ServiceSpec(
        id="webterm",
        name="Web Terminal",
        process_patterns=("ttyd",),
        install_paths=("/home/linuxbrew/.linuxbrew/bin/ttyd", "/usr/bin/ttyd"),
    ),
)


def run(*args: str, timeout: float = 4.0) -> tuple[int, str]:
    try:
        p = subprocess.run(
            args, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            timeout=timeout, check=False
        )
        return p.returncode, p.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return 127, str(exc)


def read_text(path: str) -> str:
    try:
        return Path(path).read_text(errors="replace").strip()
    except OSError:
        return ""


def system_info() -> dict:
    system=platform.system()
    _, uptime_raw = run("uptime")
    uptime=uptime_raw.strip()

    total=used=available=0
    if system=="Darwin":
        _, memsize=run("sysctl","-n","hw.memsize")
        try: total=int(memsize)
        except ValueError: total=0
        # vm_stat is page based; this is intentionally an approximate operator view.
        _, vm=run("vm_stat")
        page=4096
        m=re.search(r"page size of (\d+) bytes",vm)
        if m: page=int(m.group(1))
        vals={}
        for line in vm.splitlines():
            m=re.match(r"([^:]+):\s+(\d+)",line)
            if m: vals[m.group(1)]=int(m.group(2))*page
        available=vals.get("Pages free",0)+vals.get("Pages inactive",0)+vals.get("Pages speculative",0)
        used=max(0,total-available)
        _, cpu_model=run("sysctl","-n","machdep.cpu.brand_string")
        if not cpu_model: _, cpu_model=run("sysctl","-n","hw.model")
        _, cores=run("sysctl","-n","hw.logicalcpu")
        _, os_name=run("sw_vers","-productName")
        _, os_ver=run("sw_vers","-productVersion")
        os_pretty=f"{os_name} {os_ver}".strip()
        _, root_df=run("df","-k","/")
        disk={}
        lines=root_df.splitlines()
        if len(lines)>=2:
            q=lines[-1].split()
            if len(q)>=5:
                disk={"total":int(q[1])*1024,"used":int(q[2])*1024,"available":int(q[3])*1024,"percent":q[4]}
    else:
        os_release={}
        for line in read_text("/etc/os-release").splitlines():
            if "=" in line:
                k,v=line.split("=",1); os_release[k]=v.strip('"')
        os_pretty=os_release.get("PRETTY_NAME",system or "Unix")
        _, mem=run("free","-b")
        for line in mem.splitlines():
            if line.startswith("Mem:"):
                q=line.split(); total,used,available=int(q[1]),int(q[2]),int(q[6])
        _, root_df=run("df","-B1","--output=size,used,avail,pcent","/")
        disk={}
        lines=root_df.splitlines()
        if len(lines)>=2:
            q=lines[-1].split()
            if len(q)>=4: disk={"total":int(q[0]),"used":int(q[1]),"available":int(q[2]),"percent":q[3]}
        _, cpu=run("lscpu")
        cpu_model=next((x.split(":",1)[1].strip() for x in cpu.splitlines() if x.startswith("Model name:")),platform.processor() or "unknown")
        cores=next((x.split(":",1)[1].strip() for x in cpu.splitlines() if x.startswith("CPU(s):")),str(os.cpu_count() or "?"))
    return {"hostname":socket.gethostname(),"os":os_pretty,"kernel":platform.release(),
            "uptime":uptime,"cpu":cpu_model.strip(),"logical_cpus":str(cores).strip(),
            "memory":{"total":total,"used":used,"available":available},"disk_root":disk}


def gpu_info() -> dict:
    if not shutil.which("nvidia-smi"):
        return {"available": False}
    fields = "name,driver_version,memory.total,memory.used,memory.free,temperature.gpu,utilization.gpu,power.draw"
    rc, out = run("nvidia-smi", f"--query-gpu={fields}", "--format=csv,noheader,nounits")
    if rc != 0 or not out:
        return {"available": False, "error": out}
    p = [x.strip() for x in out.splitlines()[0].split(",")]
    return {
        "available": True, "name": p[0], "driver": p[1],
        "vram_total_mib": int(p[2]), "vram_used_mib": int(p[3]),
        "vram_free_mib": int(p[4]), "temperature_c": int(p[5]),
        "utilization_percent": int(p[6]), "power_w": float(p[7]),
    }


def systemd_state(unit: str, user: bool = False) -> dict:
    if platform.system()!="Linux" or not shutil.which("systemctl"):
        return {"exists":False,"active":False,"state":"unsupported","substate":"","enabled":False,"main_pid":"0","since":"","unit_path":"","exec_status":""}
    prefix = ("systemctl", "--user") if user else ("systemctl",)
    rc, active = run(*prefix, "is-active", unit)
    _, enabled = run(*prefix, "is-enabled", unit)
    _, show = run(
        *prefix, "show", unit,
        "--property=LoadState,ActiveState,SubState,MainPID,ActiveEnterTimestamp,FragmentPath,ExecMainStatus"
    )
    props = {}
    for line in show.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            props[key] = value

    load_state = props.get("LoadState", "not-found")
    return {
        "exists": load_state not in ("not-found", ""),
        "active": props.get("ActiveState") == "active",
        "state": props.get("ActiveState", active),
        "substate": props.get("SubState", ""),
        "enabled": enabled == "enabled",
        "main_pid": props.get("MainPID", "0"),
        "since": props.get("ActiveEnterTimestamp", ""),
        "unit_path": props.get("FragmentPath", ""),
        "exec_status": props.get("ExecMainStatus", ""),
    }


def process_matches(patterns: tuple[str, ...]) -> list[str]:
    _, out = run("ps", "-eo", "pid=,user=,cmd=", timeout=5)
    found = []
    for line in out.splitlines():
        if any(p.lower() in line.lower() for p in patterns):
            if "server.py" not in line:
                found.append(line.strip())
    return found


def port_listening(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1",port),timeout=.25):
            return True
    except OSError:
        return False


def http_health(port: int, path: str) -> tuple[bool, str]:
    url = f"http://127.0.0.1:{port}{path}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "3090-server/0.1"})
        with urllib.request.urlopen(req, timeout=1.5) as r:
            return 200 <= r.status < 500, f"HTTP {r.status}"
    except Exception as exc:
        return False, exc.__class__.__name__


def tailscale_info() -> dict:
    tailscale=shutil.which("tailscale")
    if not tailscale:
        return {"installed": False}

    rc, status = run(tailscale, "status")
    warning = ""
    clean = []
    for line in status.splitlines():
        if line.startswith("Warning:"):
            warning = line
        else:
            clean.append(line)

    _, ips = run(tailscale, "ip")
    ip_lines = [x for x in ips.splitlines() if not x.startswith("Warning:")]
    _, serve = run("/usr/bin/tailscale", "serve", "status")
    serve_clean = "\n".join(x for x in serve.splitlines() if not x.startswith("Warning:"))

    name = ""
    ipv4 = next((x for x in ip_lines if "." in x), "")
    for line in clean:
        if ipv4 and line.startswith(ipv4):
            parts = line.split()
            if len(parts) > 1:
                name = parts[1]
            break

    return {
        "installed": True,
        "connected": rc == 0 and bool(ipv4),
        "ipv4": ipv4,
        "name": name,
        "warning": warning,
        "serve": serve_clean,
    }


def tailnet_route_for(port: Optional[int], serve: str) -> Optional[str]:
    if not port:
        return None
    blocks = serve.split("\n\n")
    needle = f":{port}"
    for block in blocks:
        if f"localhost:{port}" in block or f"127.0.0.1:{port}" in block:
            first = block.splitlines()[0].strip()
            return first.split(" ", 1)[0]
    return None


def installed_paths(spec: ServiceSpec) -> list[str]:
    found = []
    for raw in spec.install_paths:
        path = Path(os.path.expanduser(raw))
        if path.exists():
            found.append(str(path))
    return found


def service_state(spec: ServiceSpec, ts: dict) -> dict:
    sd = systemd_state(spec.system_unit) if spec.system_unit else (
        systemd_state(spec.user_unit, user=True) if spec.user_unit else None
    )
    procs = process_matches(spec.process_patterns)
    listening = port_listening(spec.port) if spec.port else False
    healthy, health_detail = (http_health(spec.port, spec.health_path) if spec.port and listening else (False, "not listening"))
    paths = installed_paths(spec)

    running = bool((sd and sd["active"]) or procs or listening)
    if sd and sd.get("state") == "failed":
        lifecycle = "failed"
    elif sd and sd["active"]:
        lifecycle = "systemd"
    elif running:
        lifecycle = "unmanaged"
    elif sd and sd.get("exists"):
        lifecycle = "systemd"
    elif paths:
        lifecycle = "installed"
    else:
        lifecycle = "missing"

    return {
        "id": spec.id,
        "name": spec.name,
        "running": running,
        "lifecycle": lifecycle,
        "authority": (
            f"system:{spec.system_unit}" if spec.system_unit and sd and sd.get("exists")
            else f"user:{spec.user_unit}" if spec.user_unit and sd and sd.get("exists")
            else "process-discovery"
        ),
        "port": spec.port,
        "listening": listening,
        "healthy": healthy,
        "health_detail": health_detail,
        "systemd": sd,
        "processes": procs,
        "paths": paths,
        "tailnet_url": tailnet_route_for(spec.port, ts.get("serve", "")),
        "gpu": spec.gpu,
    }


def ollama_details() -> dict:
    exe = shutil.which("ollama")
    if not exe:
        return {}
    _, version = run(exe, "--version")
    _, models = run(exe, "list")
    _, loaded = run(exe, "ps")
    proxy_ok, proxy_detail=http_health(11435,"/api/version") if port_listening(11435) else (False,"not listening")
    return {"cli": exe, "version": version, "models": models, "loaded": loaded,
            "local_api": http_health(11434,"/api/version")[0] if port_listening(11434) else False,
            "share_proxy": {"port":11435,"healthy":proxy_ok,"detail":proxy_detail}}


def warnings(snapshot: dict) -> list[str]:
    out = []
    ts = snapshot["tailscale"]
    if ts.get("warning"):
        out.append("Tailscale client/daemon build mismatch")

    # Known duplicate discovered by the first forensic audit.
    if platform.system()=="Linux" and shutil.which("systemctl"):
        rc, state = run("systemctl", "--user", "is-enabled", "sh.brew.ollama.service")
        if rc == 0 or state == "enabled":
            out.append("duplicate Homebrew Ollama user service is enabled")

    by_id = {s["id"]: s for s in snapshot["services"]}
    for sid in ("comfy", "mercury"):
        s = by_id[sid]
        if s["running"] and s["lifecycle"] == "unmanaged":
            out.append(f"{s['name']} is running outside a dedicated systemd service")
        elif s["lifecycle"] == "installed":
            out.append(f"{s['name']} is installed but has no managed lifecycle")

    for svc in by_id.values():
        if svc.get("tailnet_url") and not svc.get("healthy"):
            out.append(f"{svc['name']} is published through Tailscale but its local backend is down")
    od=snapshot.get("ollama",{})
    proxy=od.get("share_proxy",{})
    if tailnet_route_for(11435,ts.get("serve","")) and not proxy.get("healthy"):
        out.append("Ollama HTTPS :11435 is published through Tailscale but the LOOK host-rewrite proxy is down")
    return out


def snapshot() -> dict:
    ts = tailscale_info()
    snap = {
        "version": VERSION,
        "system": system_info(),
        "gpu": gpu_info(),
        "tailscale": ts,
        "services": [service_state(s, ts) for s in SERVICES],
        "ollama": ollama_details(),
    }
    snap["warnings"] = warnings(snap)
    return snap


def gib(n: int) -> str:
    return f"{n / (1024**3):.1f} GiB"


def status(snap: dict, only: Optional[str] = None) -> None:
    services = snap["services"]
    if only:
        services = [s for s in services if s["id"] == only or s["name"].lower() == only.lower()]
        if not services:
            print(f"Unknown service: {only}", file=sys.stderr)
            print("Known: " + ", ".join(s["id"] for s in snap["services"]), file=sys.stderr)
            raise SystemExit(2)
        s = services[0]
        print(f"{s['name']}")
        print("─" * 48)
        state_label = "running" if s["running"] else ("failed" if s["lifecycle"] == "failed" else "stopped")
        print(f"State       {state_label}")
        print(f"Lifecycle   {s['lifecycle']}")
        if s["systemd"] and s["systemd"].get("exists"):
            sd = s["systemd"]
            print(f"Systemd     {sd.get('state','?')}/{sd.get('substate','?')} · {'enabled' if sd.get('enabled') else 'disabled'}")
        if s["port"]:
            print(f"Local       127.0.0.1:{s['port']}  {'✓' if s['listening'] else 'down'}")
        print(f"Health      {'✓ ' if s['healthy'] else '✗ '}{s['health_detail']}")
        if s["tailnet_url"]:
            print(f"Tailnet     {s['tailnet_url']} · backend {'healthy' if s['healthy'] else 'DOWN'}")
        else:
            print("Tailnet     not exposed")
        if s["paths"]:
            print(f"Install     {s['paths'][0]}")
        if s["systemd"] and s["systemd"]["unit_path"]:
            print(f"Unit        {s['systemd']['unit_path']}")
        if s["processes"]:
            print("Processes")
            for p in s["processes"][:5]:
                print(f"            {p}")
        return

    si, gpu, ts = snap["system"], snap["gpu"], snap["tailscale"]
    print(f"{ts.get('name') or si['hostname']}  ·  Local Labs Host")
    print("─" * 52)
    print("SYSTEM")
    print(f"  OS          {si['os']}")
    print(f"  Uptime      {si['uptime']}")
    print(f"  CPU         {si['cpu']}")
    print(f"  Memory      {gib(si['memory']['used'])} / {gib(si['memory']['total'])}")
    d = si["disk_root"]
    if d:
        print(f"  Storage     {gib(d['used'])} / {gib(d['total'])}  ({d['percent']})")

    print("\nGPU")
    if gpu.get("available"):
        print(f"  {gpu['name']}  ● ready")
        print(f"  VRAM        {gpu['vram_used_mib']/1024:.1f} / {gpu['vram_total_mib']/1024:.1f} GiB")
        print(f"  Load        {gpu['utilization_percent']}%")
        print(f"  Temp        {gpu['temperature_c']}°C")
    else:
        print("  NVIDIA      ○ unavailable")

    print("\nNETWORK")
    if ts.get("installed"):
        print(f"  Tailscale   {'● connected' if ts.get('connected') else '○ disconnected'}")
        print(f"  Node        {ts.get('name') or 'unknown'}")
        print(f"  Tailnet IP  {ts.get('ipv4') or '—'}")
    else:
        print("  Tailscale   ○ not installed")

    print("\nSERVICES")
    for s in services:
        mark = "●" if s["running"] and s["healthy"] else ("◐" if s["running"] else "○")
        state = "running" if s["running"] else ("not installed" if s["lifecycle"] == "missing" else "stopped")
        exposure = f" · tailnet ✓" if s["tailnet_url"] and s["healthy"] else (" · route/down" if s["tailnet_url"] else "")
        print(f"  {s['name']:<15} {mark} {state:<11} {s['lifecycle']}{exposure}")

    if snap["warnings"]:
        print("\nWARNINGS")
        for w in snap["warnings"]:
            print(f"  ⚠ {w}")


def discover(snap: dict, json_mode: bool = False) -> None:
    if json_mode:
        print(json.dumps(snap, indent=2))
        return
    status(snap)
    print("\nDETAILS")
    print("  Discovery is read-only. Linux/systemd/Tailscale remain authoritative.")
    print("\n  Tailscale Serve")
    if snap["tailscale"].get("serve"):
        for line in snap["tailscale"]["serve"].splitlines():
            print(f"    {line}")
    else:
        print("    none")

    print("\n  Ollama")
    od = snap.get("ollama", {})
    print(f"    CLI       {od.get('cli', 'not found')}")
    if od.get("version"):
        print(f"    {od['version']}")
    proxy=od.get("share_proxy",{})
    print(f"    API       127.0.0.1:11434 {'healthy' if od.get('local_api') else 'DOWN'}")
    print(f"    Proxy     127.0.0.1:11435 {'healthy' if proxy.get('healthy') else 'DOWN'}")
    route=tailnet_route_for(11435,snap["tailscale"].get("serve",""))
    print(f"    Tailnet   {route or 'not exposed'}")
    if od.get("loaded"):
        print("    Loaded:")
        for line in od["loaded"].splitlines():
            print(f"      {line}")

    authority_report(snap)

    print("\n  Service paths")
    for s in snap["services"]:
        if s["paths"]:
            for p in s["paths"]:
                print(f"    {s['name']:<15} {p}")



def get_spec(name: str) -> ServiceSpec:
    aliases={"decision":"openjev","jev":"openjev"}
    name=aliases.get(str(name).lower(),name)
    for spec in SERVICES:
        if spec.id == name or spec.name.lower() == str(name).lower():
            return spec
    print(f"Unknown service: {name}", file=sys.stderr)
    print("Known: " + ", ".join(s.id for s in SERVICES), file=sys.stderr)
    raise SystemExit(2)


def service_unit(spec: ServiceSpec) -> tuple[tuple[str, ...], Optional[str]]:
    if spec.system_unit:
        return ("systemctl",), spec.system_unit
    if spec.user_unit:
        return ("systemctl", "--user"), spec.user_unit
    return (), None


def action(name: str, service_name: str) -> None:
    spec = get_spec(service_name)
    prefix, unit = service_unit(spec)
    if not unit:
        print(f"{spec.name} has no managed lifecycle yet.")
        raise SystemExit(2)

    cmd = list(prefix) + [name, unit]
    if spec.system_unit and name in ("start", "stop", "restart"):
        cmd = ["sudo"] + cmd

    verb = {"start": "Starting", "stop": "Stopping", "restart": "Restarting"}[name]
    print(f"{verb} {spec.name}…")
    rc = subprocess.call(cmd)
    if rc != 0:
        print(f"\n{spec.name}: systemd command failed (exit {rc}).", file=sys.stderr)
        raise SystemExit(rc)

    import time
    if name in ("start", "restart") and spec.port:
        deadline = time.monotonic() + 8.0
        while time.monotonic() < deadline:
            if port_listening(spec.port):
                ok, _ = http_health(spec.port, spec.health_path)
                if ok:
                    break
            time.sleep(0.4)

    snap = snapshot()
    status(snap, spec.id)
    current = next(x for x in snap["services"] if x["id"] == spec.id)

    if name in ("start", "restart") and not current["healthy"]:
        print("\nStart completed but the service did not become healthy.", file=sys.stderr)
        print("Recent journal:", file=sys.stderr)
        cmd = ["journalctl"]
        if spec.user_unit:
            cmd.append("--user")
        cmd += ["-u", unit, "-n", "25", "--no-pager"]
        subprocess.call(cmd)
        raise SystemExit(1)


def logs(service_name: str) -> None:
    spec = get_spec(service_name)
    prefix, unit = service_unit(spec)
    if not unit:
        print(f"{spec.name} has no journal-backed managed service yet.")
        raise SystemExit(2)
    cmd = ["journalctl"]
    if spec.user_unit:
        cmd.append("--user")
    cmd += ["-u", unit, "-n", "100", "--no-pager"]
    subprocess.call(cmd)


def start_all() -> None:
    # Do not restart already-running services; only start managed services that are down.
    snap = snapshot()
    states = {s["id"]: s for s in snap["services"]}
    for spec in SERVICES:
        _, unit = service_unit(spec)
        state=states[spec.id]
        # Optional decision workers remain opt-in; `server start openjev` is explicit.
        if spec.id=="openjev" and not ((state.get("systemd") or {}).get("enabled")):
            continue
        if unit and not state["running"]:
            action("start", spec.id)



def pid_command(pid: int) -> str:
    _, out = run("ps", "-p", str(pid), "-o", "cmd=")
    return out.strip()


def comfy_unmanaged_pids() -> list[int]:
    """Return only the actual Comfy main process on our canonical port/install."""
    _, out = run("ps", "-eo", "pid=,cmd=", timeout=5)
    pids = []
    canonical = str(HOME / ".local/share/look/services/comfyui")
    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split(None, 1)
        if len(parts) != 2:
            continue
        pid_s, cmd = parts
        if (
            "main.py" in cmd
            and "--port 8188" in cmd
            and canonical in cmd
            and "server-comfy.service" not in cmd
        ):
            try:
                pids.append(int(pid_s))
            except ValueError:
                pass
    return pids


def wait_port(port: int, wanted: bool, timeout: float) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if port_listening(port) == wanted:
            return True
        time.sleep(0.25)
    return port_listening(port) == wanted


def migrate_comfy() -> None:
    spec = get_spec("comfy")
    sd = systemd_state(spec.user_unit, user=True)

    if sd.get("active"):
        print("ComfyUI is already systemd-managed.")
        status(snapshot(), "comfy")
        return

    pids = comfy_unmanaged_pids()
    if len(pids) > 1:
        print("Refusing migration: more than one canonical Comfy main process was found.", file=sys.stderr)
        for pid in pids:
            print(f"  PID {pid}: {pid_command(pid)}", file=sys.stderr)
        raise SystemExit(1)

    if not pids:
        if port_listening(8188):
            print("Refusing migration: port 8188 is occupied, but not by the expected Comfy process.", file=sys.stderr)
            print("Run: server discover", file=sys.stderr)
            raise SystemExit(1)
        print("No unmanaged Comfy process is running; starting the systemd service.")
        action("start", "comfy")
        return

    pid = pids[0]
    cmd = pid_command(pid)
    print("ComfyUI migration")
    print("────────────────────────────────────────────────")
    print(f"Found       unmanaged PID {pid}")
    print(f"Install     {HOME}/.local/share/look/services/comfyui")
    print("Port        127.0.0.1:8188")
    print()
    print("This will stop that Comfy process and immediately restart the same")
    print("installation under server-comfy.service.")
    answer = input("Migrate ComfyUI now? [y/N] ").strip().lower()
    if answer not in ("y", "yes"):
        print("Migration cancelled. Nothing changed.")
        return

    print(f"Stopping unmanaged ComfyUI PID {pid}…")
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    except PermissionError:
        print("Could not signal the Comfy process; no further changes made.", file=sys.stderr)
        raise SystemExit(1)

    # Give Comfy time to release GPU state and the HTTP port cleanly.
    if not wait_port(8188, False, 12.0):
        print("Comfy did not release port 8188 after SIGTERM.", file=sys.stderr)
        print("Refusing to SIGKILL it automatically. Migration stopped.", file=sys.stderr)
        raise SystemExit(1)

    print("Port 8188 released.")
    print("Starting server-comfy.service…")
    rc = subprocess.call(["systemctl", "--user", "start", spec.user_unit])
    if rc != 0:
        print("systemd could not start ComfyUI.", file=sys.stderr)
        print("Recent journal:", file=sys.stderr)
        subprocess.call(["journalctl", "--user", "-u", spec.user_unit, "-n", "30", "--no-pager"])
        raise SystemExit(rc)

    deadline = time.monotonic() + 20.0
    healthy = False
    while time.monotonic() < deadline:
        if port_listening(8188):
            healthy, _ = http_health(8188, spec.health_path)
            if healthy:
                break
        time.sleep(0.5)

    if not healthy:
        print("ComfyUI did not become healthy after migration.", file=sys.stderr)
        subprocess.call(["journalctl", "--user", "-u", spec.user_unit, "-n", "40", "--no-pager"])
        raise SystemExit(1)

    print()
    print("Migration complete.")
    status(snapshot(), "comfy")


def ollama_cleanup_status() -> dict:
    unit = "sh.brew.ollama.service"
    state = systemd_state(unit, user=True)
    canonical = systemd_state("ollama.service", user=False)
    return {"brew": state, "canonical": canonical}


def cleanup_ollama() -> None:
    info = ollama_cleanup_status()
    brew = info["brew"]
    canonical = info["canonical"]

    print("Ollama lifecycle cleanup")
    print("────────────────────────────────────────────────")
    print(f"Canonical   ollama.service · {canonical.get('state','?')}/{canonical.get('substate','?')}")
    print(f"Homebrew    sh.brew.ollama.service · {brew.get('state','?')}/{brew.get('substate','?')}")
    print()

    if not canonical.get("active"):
        print("Refusing cleanup: canonical system ollama.service is not active.", file=sys.stderr)
        raise SystemExit(1)

    if not brew.get("exists"):
        print("No Homebrew Ollama user service exists. Nothing to clean up.")
        return

    if not brew.get("enabled") and not brew.get("active"):
        print("Homebrew Ollama user service is already inactive and disabled.")
        return

    print("This disables/stops only the redundant Homebrew USER service.")
    print("It does NOT uninstall the Homebrew Ollama CLI or delete models/configuration.")
    answer = input("Retire redundant Homebrew Ollama service? [y/N] ").strip().lower()
    if answer not in ("y", "yes"):
        print("Cleanup cancelled. Nothing changed.")
        return

    rc = subprocess.call(["systemctl", "--user", "disable", "--now", "sh.brew.ollama.service"])
    if rc != 0:
        print("Could not disable the Homebrew Ollama user service.", file=sys.stderr)
        raise SystemExit(rc)

    canonical_after = systemd_state("ollama.service", user=False)
    if not canonical_after.get("active"):
        print("WARNING: canonical Ollama is no longer active; investigate immediately.", file=sys.stderr)
        raise SystemExit(1)

    ok, detail = http_health(11434, "/api/version")
    if not ok:
        print(f"WARNING: canonical Ollama failed health check: {detail}", file=sys.stderr)
        raise SystemExit(1)

    print()
    print("Cleanup complete.")
    print("Canonical ollama.service remains active and healthy.")
    print("Homebrew Ollama CLI remains installed.")


def authority_report(snap: dict) -> None:
    print("\n  Lifecycle authority")
    for service in snap["services"]:
        print(f"    {service['name']:<15} {service['authority']}")


def install_searxng() -> None:
    spec = get_spec("searxng")
    existing = service_state(spec, tailscale_info())

    # A partial upstream install can create the searxng user/directories before failing.
    # Do not confuse that with a healthy completed installation.
    if existing["healthy"]:
        print("SearXNG is already installed and healthy.")
        status(snapshot(), "searxng")
        return

    if not shutil.which("git"):
        print("git is required to install SearXNG.", file=sys.stderr)
        raise SystemExit(1)

    stage_root = Path("/tmp/3090-searxng-install")
    repo = stage_root / "searxng"

    print("SearXNG installation")
    print("────────────────────────────────────────────────")
    if existing["paths"]:
        print("State        partial/existing installation detected")
    else:
        print("State        not installed")
    print("Source       official searxng/searxng repository")
    print(f"Staging      {repo}")
    print("Bind target  127.0.0.1:8888")
    print("Exposure     local only")
    print()
    print("The staging directory is deliberately world-traversable/readable because")
    print("the upstream installer switches to its dedicated 'searxng' user.")
    print("Only temporary public source code is staged there; no secrets are stored there.")
    print()
    answer = input("Install/repair SearXNG now? [y/N] ").strip().lower()
    if answer not in ("y", "yes"):
        print("Installation cancelled. Nothing changed.")
        return

    # Clean only our own known staging directory. Never touch /usr/local/searxng
    # or /etc/searxng here; those belong to the upstream installer.
    if stage_root.exists():
        shutil.rmtree(stage_root)
    stage_root.mkdir(mode=0o755, parents=True)
    os.chmod(stage_root, 0o755)

    print("\nCloning official SearXNG source…")
    rc = subprocess.call([
        "git", "clone", "--depth", "1",
        "https://github.com/searxng/searxng.git", str(repo)
    ])
    if rc != 0:
        raise SystemExit(rc)

    # Git may honor a restrictive umask. The dedicated upstream service user needs
    # traversal/read access to source during install. Directories 755, files 644,
    # and preserve executable bits on scripts.
    for dirpath, dirnames, filenames in os.walk(repo):
        os.chmod(dirpath, 0o755)
        for filename in filenames:
            fp = Path(dirpath) / filename
            try:
                mode = fp.stat().st_mode
                os.chmod(fp, 0o755 if (mode & 0o111) else 0o644)
            except OSError:
                pass

    script = repo / "utils" / "searxng.sh"
    if not script.exists():
        print("Upstream installation script not found; refusing to improvise.", file=sys.stderr)
        raise SystemExit(1)

    print("\nRunning upstream installation/repair…")
    rc = subprocess.call(["sudo", "-H", str(script), "install", "all"], cwd=str(repo))
    if rc != 0:
        print("SearXNG upstream installer failed.", file=sys.stderr)
        print(f"Staging retained for inspection: {repo}", file=sys.stderr)
        raise SystemExit(rc)

    print("\nValidating localhost:8888…")
    deadline = time.monotonic() + 20.0
    healthy = False
    detail = ""
    while time.monotonic() < deadline:
        healthy, detail = http_health(8888, "/")
        if healthy:
            break
        time.sleep(0.5)

    snap = snapshot()
    status(snap, "searxng")

    if not healthy:
        print(f"\nSearXNG install completed but health check failed: {detail}", file=sys.stderr)
        print("The upstream install has been preserved; nothing will be deleted automatically.", file=sys.stderr)
        raise SystemExit(1)

    # Cleanup only successful staging.
    shutil.rmtree(stage_root, ignore_errors=True)
    print()
    print("SearXNG is healthy on localhost:8888.")
    print("Temporary installation source removed.")
    print("Tailnet exposure remains intentionally disabled.")



def normalize_searxng() -> None:
    src_ini = Path("/etc/uwsgi/apps-available/searxng.ini")
    if not src_ini.exists():
        print("SearXNG uWSGI configuration was not found.", file=sys.stderr)
        print("Run: server install searxng", file=sys.stderr)
        raise SystemExit(1)

    print("Normalize SearXNG")
    print("────────────────────────────────────────────────")
    print("Current      upstream Debian uWSGI socket")
    print("Target       server-searxng.service")
    print("HTTP         127.0.0.1:8888")
    print("Edge         Tailscale Serve later; nginx not required")
    print()
    print("This preserves the upstream SearXNG install and settings.")
    print("It disables only the enabled Debian SearXNG uWSGI app, creates a")
    print("dedicated systemd service, and repairs the dangling nginx SearXNG link")
    print("left by the failed HTTP-site installation.")
    answer = input("Normalize SearXNG now? [y/N] ").strip().lower()
    if answer not in ("y", "yes"):
        print("Normalization cancelled. Nothing changed.")
        return

    # Build our uWSGI config from the upstream one, changing only the transport.
    text = src_ini.read_text()
    lines = []
    replaced = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("socket") and "=" in stripped:
            lines.append("http-socket = 127.0.0.1:8888")
            replaced = True
        else:
            lines.append(line)
    if not replaced:
        print("Refusing normalization: expected upstream 'socket =' directive not found.", file=sys.stderr)
        raise SystemExit(1)

    import tempfile
    with tempfile.NamedTemporaryFile("w", delete=False, prefix="3090-searxng-", suffix=".ini") as f:
        f.write("\n".join(lines) + "\n")
        tmp_ini = f.name

    unit_text = """[Unit]
Description=3090 SearXNG
After=network-online.target valkey-server.service
Wants=network-online.target
Requires=valkey-server.service

[Service]
Type=simple
User=searxng
Group=searxng
ExecStart=/usr/bin/uwsgi --ini /etc/3090-server/searxng.ini
Restart=on-failure
RestartSec=3

[Install]
WantedBy=multi-user.target
"""
    with tempfile.NamedTemporaryFile("w", delete=False, prefix="3090-searxng-", suffix=".service") as f:
        f.write(unit_text)
        tmp_unit = f.name

    try:
        print("\nInstalling normalized service…")
        subprocess.check_call(["sudo", "mkdir", "-p", "/etc/3090-server"])
        subprocess.check_call(["sudo", "install", "-m", "0644", tmp_ini, "/etc/3090-server/searxng.ini"])
        subprocess.check_call(["sudo", "install", "-m", "0644", tmp_unit, "/etc/systemd/system/server-searxng.service"])

        # Stop only the upstream SearXNG vassal/instance before disabling its symlink.
        subprocess.call(["sudo", "service", "uwsgi", "stop", "searxng"])
        enabled = Path("/etc/uwsgi/apps-enabled/searxng.ini")
        if enabled.exists() or enabled.is_symlink():
            subprocess.check_call(["sudo", "rm", "-f", str(enabled)])

        # Repair only the failed SearXNG nginx edge. Keep nginx/package/default config.
        broken = Path("/etc/nginx/default.d/searxng.conf")
        if broken.is_symlink() and not broken.exists():
            print("Removing dangling nginx SearXNG link…")
            subprocess.check_call(["sudo", "rm", "-f", str(broken)])

        # Validate nginx after our narrow repair; do not make nginx part of SearXNG.
        if shutil.which("nginx"):
            rc = subprocess.call(["sudo", "nginx", "-t"])
            if rc != 0:
                print("WARNING: nginx still has an unrelated configuration problem.", file=sys.stderr)
                print("SearXNG normalization will continue; nginx is not required.", file=sys.stderr)

        subprocess.check_call(["sudo", "systemctl", "daemon-reload"])
        subprocess.check_call(["sudo", "systemctl", "enable", "--now", "server-searxng.service"])

        deadline = time.monotonic() + 20.0
        healthy = False
        detail = ""
        while time.monotonic() < deadline:
            healthy, detail = http_health(8888, "/")
            if healthy:
                break
            time.sleep(0.5)

        if not healthy:
            print(f"\nSearXNG service started but health failed: {detail}", file=sys.stderr)
            subprocess.call(["sudo", "journalctl", "-u", "server-searxng.service", "-n", "50", "--no-pager"])
            raise SystemExit(1)

        print()
        print("Normalization complete.")
        status(snapshot(), "searxng")
        print()
        print("nginx is not in the SearXNG request path.")
        print("Tailnet exposure remains disabled.")
    finally:
        for f in (tmp_ini, tmp_unit):
            try:
                os.unlink(f)
            except OSError:
                pass


def tailnet_expose(service_name: str, enable: bool) -> None:
    spec = get_spec(service_name)
    if not spec.port:
        print(f"{spec.name} has no declared HTTP port.", file=sys.stderr)
        raise SystemExit(2)

    snap = snapshot()
    current = next(x for x in snap["services"] if x["id"] == spec.id)

    if enable:
        if not current["healthy"]:
            print(f"Refusing exposure: {spec.name} is not locally healthy.", file=sys.stderr)
            print(f"Expected healthy endpoint on 127.0.0.1:{spec.port}.", file=sys.stderr)
            raise SystemExit(1)

        if current.get("tailnet_url"):
            print(f"{spec.name} is already exposed to the tailnet.")
            status(snap, spec.id)
            return

        print(f"Exposing {spec.name} privately through Tailscale Serve…")
        rc = subprocess.call([
            "tailscale", "serve", "--bg",
            f"--https={spec.port}",
            f"localhost:{spec.port}",
        ])
        if rc != 0:
            print("Tailscale Serve failed; no controller state was changed.", file=sys.stderr)
            raise SystemExit(rc)

        time.sleep(0.5)
        after = snapshot()
        svc = next(x for x in after["services"] if x["id"] == spec.id)
        if not svc.get("tailnet_url"):
            print("Serve command succeeded, but the expected route was not discovered.", file=sys.stderr)
            print("Run: tailscale serve status", file=sys.stderr)
            raise SystemExit(1)

        print()
        status(after, spec.id)
        return

    # Disable only this service's HTTPS port. Never reset the whole Serve config.
    if not current.get("tailnet_url"):
        print(f"{spec.name} is not exposed to the tailnet. Nothing changed.")
        return

    print(f"Removing {spec.name} from Tailscale Serve…")
    rc = subprocess.call([
        "tailscale", "serve",
        f"--https={spec.port}", "off",
    ])
    if rc != 0:
        print("Tailscale Serve removal failed.", file=sys.stderr)
        raise SystemExit(rc)

    time.sleep(0.5)
    after = snapshot()
    svc = next(x for x in after["services"] if x["id"] == spec.id)
    if svc.get("tailnet_url"):
        print("The route still appears to be configured.", file=sys.stderr)
        raise SystemExit(1)

    print()
    status(after, spec.id)


def searxng_api_check() -> None:
    spec = get_spec("searxng")
    ok, detail = http_health(spec.port, "/")
    if not ok:
        print(f"SearXNG is not locally healthy: {detail}", file=sys.stderr)
        raise SystemExit(1)

    import json
    from urllib.parse import urlencode
    from urllib.request import urlopen
    from urllib.error import HTTPError, URLError

    query = urlencode({"q": "SearXNG", "format": "json"})
    url = f"http://127.0.0.1:{spec.port}/search?{query}"
    print("Testing SearXNG JSON API…")
    try:
        with urlopen(url, timeout=20) as response:
            body = response.read(1024 * 1024)
            code = response.status
        data = json.loads(body)
        results = data.get("results", []) if isinstance(data, dict) else []
        if code == 200 and isinstance(data, dict):
            print("JSON API      ✓ HTTP 200")
            print(f"Search results {len(results)}")
            if results:
                title = str(results[0].get("title", "")).strip()
                if title:
                    print(f"First result   {title[:100]}")
            return
        print(f"JSON API      ✗ HTTP {code}", file=sys.stderr)
        raise SystemExit(1)
    except HTTPError as e:
        print(f"JSON API      ✗ HTTP {e.code}", file=sys.stderr)
        if e.code == 403:
            print("JSON output is probably not enabled in search.formats.", file=sys.stderr)
        elif e.code == 429:
            print("Request reached SearXNG but was rejected by its limiter.", file=sys.stderr)
            print("For this private localhost/Tailscale instance, run:", file=sys.stderr)
            print("  server configure searxng", file=sys.stderr)
        raise SystemExit(1)
    except (URLError, ValueError) as e:
        print(f"JSON API      ✗ {e}", file=sys.stderr)
        raise SystemExit(1)


def configure_searxng() -> None:
    settings = Path("/etc/searxng/settings.yml")
    backup = Path("/etc/searxng/settings.yml.3090-original")

    if not settings.exists():
        print("SearXNG settings.yml was not found.", file=sys.stderr)
        raise SystemExit(1)

    print("Configure SearXNG for private 3090 API use")
    print("────────────────────────────────────────────────")
    print("Enable       HTML + JSON search formats")
    print("Limiter      disable public-instance limiter")
    print("Security     localhost bind + Tailscale remain the access boundary")
    print("Secret       preserved; never printed")
    print()
    answer = input("Configure SearXNG now? [y/N] ").strip().lower()
    if answer not in ("y", "yes"):
        print("Configuration cancelled. Nothing changed.")
        return

    # Read through sudo because future permissions may become stricter.
    rc, original = run("sudo", "cat", str(settings))
    if rc != 0 or not original:
        print("Could not read SearXNG settings.", file=sys.stderr)
        raise SystemExit(1)

    lines = original.splitlines()
    out = []
    in_formats = False
    json_present = False
    limiter_found = False

    for line in lines:
        stripped = line.strip()

        if stripped == "formats:" and line.startswith("  "):
            in_formats = True
            json_present = False
            out.append(line)
            continue

        if in_formats:
            # List entries under search.formats are indented four spaces.
            if line.startswith("    - "):
                if stripped == "- json":
                    json_present = True
                out.append(line)
                continue
            if not json_present:
                out.append("    - json")
            in_formats = False

        if stripped.startswith("limiter:") and line.startswith("  "):
            out.append("  limiter: false")
            limiter_found = True
        else:
            out.append(line)

    if in_formats and not json_present:
        out.append("    - json")

    if not limiter_found:
        print("Refusing edit: expected server.limiter setting was not found.", file=sys.stderr)
        raise SystemExit(1)

    updated = "\n".join(out) + "\n"

    # Sanity: preserve the secret line without ever displaying its value.
    old_secret = next((x for x in lines if x.strip().startswith("secret_key:")), None)
    new_secret = next((x for x in out if x.strip().startswith("secret_key:")), None)
    if not old_secret or old_secret != new_secret:
        print("Refusing edit: secret_key would not be preserved exactly.", file=sys.stderr)
        raise SystemExit(1)

    import tempfile
    with tempfile.NamedTemporaryFile("w", delete=False, prefix="3090-searxng-settings-", suffix=".yml") as f:
        f.write(updated)
        tmp = f.name

    try:
        if not backup.exists():
            print("Creating one-time original settings backup…")
            subprocess.check_call(["sudo", "cp", "-p", str(settings), str(backup)])

        subprocess.check_call(["sudo", "install", "-o", "searxng", "-g", "searxng", "-m", "0644", tmp, str(settings)])

        restart_searxng_with_progress()
        print("HTML health   ✓ HTTP 200")
        searxng_api_check()
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass




def searxng_search(query: str, limit: int = 5) -> list[dict]:
    import json
    from urllib.parse import urlencode
    from urllib.request import urlopen
    from urllib.error import HTTPError, URLError

    params = urlencode({"q": query, "format": "json"})
    url = f"http://127.0.0.1:8888/search?{params}"
    try:
        with urlopen(url, timeout=20) as response:
            data = json.loads(response.read(2 * 1024 * 1024))
    except HTTPError as e:
        raise RuntimeError(f"SearXNG HTTP {e.code}") from e
    except URLError as e:
        raise RuntimeError(f"SearXNG unavailable: {e.reason}") from e
    except ValueError as e:
        raise RuntimeError("SearXNG returned invalid JSON") from e

    results = data.get("results", []) if isinstance(data, dict) else []
    return results[:max(1, min(limit, 20))]


def search_cli(query: str) -> None:
    query = query.strip()
    if not query:
        print("Search query cannot be empty.", file=sys.stderr)
        raise SystemExit(2)

    try:
        results = searxng_search(query, 5)
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        raise SystemExit(1)

    print(f'Search · "{query}"')
    print("────────────────────────────────────────────────")
    if not results:
        print("No results.")
        return

    for i, result in enumerate(results, 1):
        title = str(result.get("title") or "(untitled)").strip()
        url = str(result.get("url") or "").strip()
        content = " ".join(str(result.get("content") or "").split())
        print(f"{i}. {title}")
        if url:
            print(f"   {url}")
        if content:
            print(f"   {content[:220]}")
        if i != len(results):
            print()


def restart_searxng_with_progress() -> None:
    import threading

    print("Restarting SearXNG…")
    started = time.monotonic()
    proc = subprocess.Popen(
        ["sudo", "systemctl", "restart", "server-searxng.service"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )

    milestones = [(2.0, "Waiting for uWSGI workers…"), (5.0, "Still waiting for clean shutdown/start…")]
    shown = set()
    while proc.poll() is None:
        elapsed = time.monotonic() - started
        for seconds, message in milestones:
            if elapsed >= seconds and seconds not in shown:
                print(message)
                shown.add(seconds)
        if elapsed >= 20.0:
            proc.terminate()
            print("Restart exceeded 20 seconds.", file=sys.stderr)
            print("Run: sudo systemctl status server-searxng.service --no-pager -l", file=sys.stderr)
            raise SystemExit(1)
        time.sleep(0.25)

    if proc.returncode != 0:
        err = (proc.stderr.read() if proc.stderr else "").strip()
        print(f"SearXNG restart failed{': ' + err if err else '.'}", file=sys.stderr)
        raise SystemExit(proc.returncode)

    deadline = time.monotonic() + 20.0
    while time.monotonic() < deadline:
        ok, _ = http_health(8888, "/")
        if ok:
            elapsed = time.monotonic() - started
            print(f"Healthy       ✓ {elapsed:.1f}s")
            return
        time.sleep(0.4)

    print("SearXNG restarted but did not become HTTP healthy.", file=sys.stderr)
    raise SystemExit(1)


def tailscale_build_details() -> None:
    rc, out = run("/usr/bin/tailscale", "version")
    if rc != 0:
        print("Tailscale version unavailable.")
        return
    print("Tailscale version")
    print("────────────────────────────────────────────────")
    print(out)
    print()
    print("If the client and tailscaled builds differ, both binaries should eventually")
    print("come from the same installation/update path. This command is diagnostic only.")


def searxng_dependency_details() -> None:
    print("SearXNG dependencies")
    print("────────────────────────────────────────────────")
    for unit in ("server-searxng.service", "valkey-server.service"):
        st = systemd_state(unit, user=False)
        print(f"{unit:<27} {st.get('state','?')}/{st.get('substate','?')}")
    rc, out = run("valkey-cli", "ping")
    if rc == 0:
        print(f"Valkey ping                 {out.strip()}")


def cleanup_tailscale() -> None:
    system_cli = Path("/usr/bin/tailscale")
    system_daemon = Path("/usr/sbin/tailscaled")
    brew_cli = Path("/home/linuxbrew/.linuxbrew/bin/tailscale")

    print("Tailscale lifecycle cleanup")
    print("────────────────────────────────────────────────")

    if not system_cli.exists() or not system_daemon.exists():
        print("Refusing cleanup: canonical system Tailscale binaries were not found.", file=sys.stderr)
        raise SystemExit(1)

    st = systemd_state("tailscaled.service", user=False)
    if st.get("state") != "active":
        print("Refusing cleanup: tailscaled.service is not active.", file=sys.stderr)
        raise SystemExit(1)

    rc, status_before = run(str(system_cli), "status", "--json")
    if rc != 0 or not status_before.strip():
        print("Refusing cleanup: /usr/bin/tailscale cannot talk to the running daemon.", file=sys.stderr)
        raise SystemExit(1)

    rc, serve_before = run(str(system_cli), "serve", "status")
    if rc != 0:
        print("Refusing cleanup: could not snapshot Tailscale Serve configuration.", file=sys.stderr)
        raise SystemExit(1)

    print("Canonical   APT/systemd · /usr/bin/tailscale + /usr/sbin/tailscaled")
    print(f"Daemon      {st.get('state','?')}/{st.get('substate','?')}")
    print(f"Homebrew    {'installed/shadowing PATH' if brew_cli.exists() else 'not installed'}")
    print()
    print("This removes only the redundant Homebrew 'tailscale' formula.")
    print("It does NOT touch daemon state, authentication, /var/lib/tailscale,")
    print("the APT package, or Tailscale Serve routes.")

    if not brew_cli.exists():
        print("\nNo redundant Homebrew Tailscale installation found.")
        return

    answer = input("Retire redundant Homebrew Tailscale? [y/N] ").strip().lower()
    if answer not in ("y", "yes"):
        print("Cleanup cancelled. Nothing changed.")
        return

    brew = shutil.which("brew") or "/home/linuxbrew/.linuxbrew/bin/brew"
    print("\nRemoving Homebrew Tailscale formula…")
    rc = subprocess.call([brew, "uninstall", "tailscale"])
    if rc != 0:
        print("Homebrew uninstall failed. System Tailscale was not changed.", file=sys.stderr)
        raise SystemExit(rc)

    # zsh/bash may cache command locations in the interactive parent shell, but the
    # controller itself now always uses /usr/bin/tailscale.
    print("Verifying canonical Tailscale…")
    rc, status_after = run(str(system_cli), "status", "--json")
    if rc != 0 or not status_after.strip():
        print("WARNING: system Tailscale verification failed after Homebrew cleanup.", file=sys.stderr)
        raise SystemExit(1)

    rc, serve_after = run(str(system_cli), "serve", "status")
    if rc != 0:
        print("WARNING: could not verify Serve configuration after cleanup.", file=sys.stderr)
        raise SystemExit(1)

    # Compare normalized text; this catches accidental route loss without parsing
    # Tailscale's human-readable Serve output.
    if serve_before.strip() != serve_after.strip():
        print("WARNING: Tailscale Serve configuration changed unexpectedly.", file=sys.stderr)
        print("Before:")
        print(serve_before)
        print("After:")
        print(serve_after)
        raise SystemExit(1)

    print("Cleanup complete.")
    print("Canonical system Tailscale remains connected.")
    print("Tailscale Serve mappings are unchanged.")
    print()
    print("Run: rehash")
    print("Then: command -v tailscale")


def doctor() -> None:
    print("3090 Doctor")
    print("────────────────────────────────────────────────")
    failures = 0

    def check(label, ok, detail=""):
        nonlocal failures
        mark = "✓" if ok else "✗"
        print(f"{mark} {label:<24} {detail}")
        if not ok:
            failures += 1

    # Core host capabilities
    check("systemd", shutil.which("systemctl") is not None)
    check("NVIDIA", shutil.which("nvidia-smi") is not None)
    rc, _ = run("/usr/bin/tailscale", "status", "--json")
    check("Tailscale", rc == 0, "connected" if rc == 0 else "unavailable")

    snap = snapshot()
    for svc in snap["services"]:
        if svc["id"] == "webterm":
            continue
        expected = svc["id"] in ("ollama", "comfy", "mercury", "searxng")
        optional_active = svc["id"] == "signal" and (svc.get("lifecycle") != "missing" or svc.get("tailnet_url"))
        if expected or optional_active:
            check(svc["name"], bool(svc.get("healthy")),
                  f"{svc.get('lifecycle','?')} · local {'ok' if svc.get('healthy') else 'down'}"
                  + (" · tailnet" if svc.get("tailnet_url") else ""))

    # SearXNG dependency + actual query
    st = systemd_state("valkey-server.service", user=False)
    check("Valkey", st.get("state") == "active", f"{st.get('state','?')}/{st.get('substate','?')}")
    try:
        results = searxng_search("3090 server health check", 1)
        check("SearXNG search", isinstance(results, list), f"{len(results)} result(s)")
    except Exception as e:
        check("SearXNG search", False, str(e))

    rc, serve = run("/usr/bin/tailscale", "serve", "status")
    check("Serve configuration", rc == 0, "readable" if rc == 0 else "unavailable")

    print("────────────────────────────────────────────────")
    if failures:
        print(f"Doctor found {failures} problem(s).")
        raise SystemExit(1)
    print("All core checks passed.")

def usage() -> None:
    print("""Local Labs Host Controller

Usage:
  server
  server status
  server status <service>
  server discover
  server discover --json
  server start <service|all>
  server stop <service>
  server restart <service>
  server logs <service>
  server cleanup ollama
  server cleanup tailscale
  server install searxng
  server normalize searxng
  server expose <service>
  server unexpose <service>
  server check searxng-api
  server configure searxng
  server search <query>
  server details searxng
  server details tailscale
  server doctor
  server console
  server version
""")


def main() -> None:
    args = sys.argv[1:]
    if not args:
        status(snapshot())
        return
    if args[0] in ("-h", "--help", "help"):
        usage()
        return
    if args[0] == "version":
        print(VERSION)
        return

    if args[0] == "status":
        snap = snapshot()
        status(snap, args[1] if len(args) > 1 else None)
        return
    if args[0] == "discover":
        discover(snapshot(), "--json" in args[1:])
        return
    if args[0] == "logs" and len(args) == 2:
        logs(args[1])
        return
    if args[0] == "cleanup" and len(args) == 2:
        if args[1] == "ollama":
            cleanup_ollama()
            return
        if args[1] == "tailscale":
            cleanup_tailscale()
            return
        print("Known cleanup targets: ollama, tailscale", file=sys.stderr)
        raise SystemExit(2)
    if args[0] == "install" and len(args) == 2:
        if args[1] != "searxng":
            print("Known install target: searxng", file=sys.stderr)
            raise SystemExit(2)
        install_searxng()
        return
    if args[0] == "normalize" and len(args) == 2:
        if args[1] != "searxng":
            print("Known normalize target: searxng", file=sys.stderr)
            raise SystemExit(2)
        normalize_searxng()
        return
    if args[0] == "expose" and len(args) == 2:
        tailnet_expose(args[1], True)
        return
    if args[0] == "unexpose" and len(args) == 2:
        tailnet_expose(args[1], False)
        return
    if args[0] == "check" and len(args) == 2:
        if args[1] != "searxng-api":
            print("Known check target: searxng-api", file=sys.stderr)
            raise SystemExit(2)
        searxng_api_check()
        return
    if args[0] == "configure" and len(args) == 2:
        if args[1] != "searxng":
            print("Known configure target: searxng", file=sys.stderr)
            raise SystemExit(2)
        configure_searxng()
        return
    if args[0] == "search" and len(args) >= 2:
        search_cli(" ".join(args[1:]))
        return
    if args[0] == "doctor" and len(args) == 1:
        doctor()
        return
    if args[0] == "console" and len(args) == 1:
        console = Path.home() / ".local/share/3090-server/console.py"
        if not console.exists():
            print("3090 console is not installed.", file=sys.stderr)
            raise SystemExit(1)
        os.execv(sys.executable, [sys.executable, str(console)])
    if args[0] == "details" and len(args) == 2:
        if args[1] == "searxng":
            searxng_dependency_details()
            return
        if args[1] == "tailscale":
            tailscale_build_details()
            return
        print("Known detail targets: searxng, tailscale", file=sys.stderr)
        raise SystemExit(2)
    if args[0] in ("start", "stop", "restart") and len(args) == 2:
        if args[0] == "start" and args[1] == "all":
            start_all()
        else:
            action(args[0], args[1])
        return

    usage()
    raise SystemExit(2)


if __name__ == "__main__":
    main()
