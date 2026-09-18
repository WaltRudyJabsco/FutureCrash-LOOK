#!/usr/bin/env python3
"""Future Crash + LOOK Unified Node 4.0.

Small shared nervous system. It does not replace Unix, Ollama, Tailscale, LOOK,
or Signal; it gives them one truthful place to publish activity and discover peers.
"""
from __future__ import annotations
import argparse,json,os,platform,shutil,socket,subprocess,threading,time,uuid
from dataclasses import dataclass,asdict
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

VERSION="4.0.0"; DEFAULT_HOST="127.0.0.1"; DEFAULT_PORT=7332
STATE=Path.home()/".local/share/future-crash-look"; STATE.mkdir(parents=True,exist_ok=True)
PRIORITY={"interactive":0,"followup":1,"background":2}

def now(): return time.time()
def probe(host,port,timeout=.12):
    try:
        with socket.create_connection((host,port),timeout): return True
    except OSError:return False

def run(*args,timeout=1.5):
    try:return subprocess.run(args,text=True,capture_output=True,timeout=timeout)
    except Exception:return None

@dataclass
class Lease:
    id:str; owner:str; priority:str; phase:str; detail:str; started:float; last_progress:float
    def public(self):
        d=asdict(self); t=now(); d["elapsed_ms"]=int((t-self.started)*1000); d["idle_ms"]=int((t-self.last_progress)*1000); return d

class Supervisor:
    def __init__(self): self.lock=threading.RLock(); self.active=None; self.history=[]
    def acquire(self,owner,priority="interactive",phase="accepted",detail=""):
        priority=priority if priority in PRIORITY else "interactive"
        with self.lock:
            if self.active:
                # Background work must never claim the lane ahead of a person. A future
                # executor can preempt it; 4.0 exposes the condition truthfully first.
                return None,self.active.public()
            t=now(); self.active=Lease(uuid.uuid4().hex[:10],owner,priority,phase,detail,t,t)
            return self.active.public(),None
    def progress(self,rid,phase=None,detail=None):
        with self.lock:
            if not self.active or self.active.id!=rid:return False
            if phase:self.active.phase=str(phase)
            if detail is not None:self.active.detail=str(detail)
            self.active.last_progress=now(); return True
    def release(self,rid,status="ok",detail=""):
        with self.lock:
            if not self.active or self.active.id!=rid:return False
            d=self.active.public(); d.update(status=status,finished=now(),final_detail=detail)
            self.history.append(d); self.history=self.history[-32:]; self.active=None; return True
    def status(self):
        with self.lock:return {"active":self.active.public() if self.active else None,"recent":self.history[-5:]}
SUP=Supervisor()

def capabilities():
    caps={"filesystem":True,"shell":True,"look":bool(shutil.which("lk")),"lo":bool(shutil.which("lo") or shutil.which("lk")),
          "tailscale":bool(shutil.which("tailscale")),"ollama":probe("127.0.0.1",11434),"signal":probe("127.0.0.1",7331),
          "node":True}
    caps["comfyui"]=probe("127.0.0.1",8188); caps["mercury"]=probe("127.0.0.1",8888)
    return caps

def peers():
    ts=shutil.which("tailscale")
    if not ts:return []
    p=run(ts,"status","--json",timeout=2)
    if not p or p.returncode:return []
    try:d=json.loads(p.stdout)
    except Exception:return []
    result=[]
    for peer in (d.get("Peer") or {}).values():
        dns=(peer.get("DNSName") or "").rstrip("."); ips=peer.get("TailscaleIPs") or []
        result.append({"name":peer.get("HostName") or dns or (ips[0] if ips else "peer"),"dns":dns,"ips":ips,"online":bool(peer.get("Online"))})
    return sorted(result,key=lambda x:(not x["online"],x["name"].lower()))

def node_info():
    return {"name":socket.gethostname(),"version":VERSION,"platform":platform.system().lower(),"architecture":platform.machine(),
            "capabilities":capabilities(),"supervisor":SUP.status()}

class API(BaseHTTPRequestHandler):
    server_version="FCLNode/4.0"
    def log_message(self,*a):pass
    def sendj(self,code,obj):
        b=json.dumps(obj,separators=(",",":"),ensure_ascii=False).encode(); self.send_response(code); self.send_header("Content-Type","application/json"); self.send_header("Content-Length",str(len(b))); self.end_headers(); self.wfile.write(b)
    def body(self):
        try:return json.loads(self.rfile.read(int(self.headers.get("Content-Length","0"))) or b"{}")
        except Exception:return {}
    def do_GET(self):
        path=urlparse(self.path).path
        if path in ("/health","/v1/health"):return self.sendj(200,{"ok":True,"version":VERSION})
        if path in ("/node","/v1/node","/v1/status"):return self.sendj(200,node_info())
        if path=="/v1/activity":return self.sendj(200,SUP.status())
        if path=="/v1/capabilities":return self.sendj(200,capabilities())
        if path=="/v1/nodes":return self.sendj(200,{"self":node_info(),"peers":peers()})
        return self.sendj(404,{"error":"not found"})
    def do_POST(self):
        path=urlparse(self.path).path; d=self.body()
        if path=="/v1/lease/acquire":
            lease,busy=SUP.acquire(str(d.get("owner") or "unknown"),str(d.get("priority") or "interactive"),str(d.get("phase") or "accepted"),str(d.get("detail") or ""))
            return self.sendj(200 if lease else 409,{"lease":lease,"busy":busy})
        if path=="/v1/lease/progress":
            ok=SUP.progress(str(d.get("id") or ""),d.get("phase"),d.get("detail")); return self.sendj(200 if ok else 404,{"ok":ok})
        if path=="/v1/lease/release":
            ok=SUP.release(str(d.get("id") or ""),str(d.get("status") or "ok"),str(d.get("detail") or "")); return self.sendj(200 if ok else 404,{"ok":ok})
        return self.sendj(404,{"error":"not found"})

def main():
    ap=argparse.ArgumentParser(description="Future Crash + LOOK unified node")
    ap.add_argument("command",nargs="?",default="serve",choices=["serve","status","nodes","activity"]); ap.add_argument("--host",default=DEFAULT_HOST); ap.add_argument("--port",type=int,default=DEFAULT_PORT)
    a=ap.parse_args()
    if a.command=="status": print(json.dumps(node_info(),indent=2)); return
    if a.command=="nodes": print(json.dumps({"self":node_info(),"peers":peers()},indent=2)); return
    if a.command=="activity": print(json.dumps(SUP.status(),indent=2)); return
    srv=ThreadingHTTPServer((a.host,a.port),API); print(f"Future Crash + LOOK node {VERSION} · http://{a.host}:{a.port}",flush=True)
    try:srv.serve_forever(poll_interval=.2)
    except KeyboardInterrupt:pass
    finally:srv.server_close()
if __name__=="__main__":main()
