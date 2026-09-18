#!/usr/bin/env python3
import json, os, subprocess, sys, time
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

HOST="127.0.0.1"; PORT=3090
SERVER=os.path.expanduser("~/.local/bin/server")

HTML=r"""<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>3090 Operator Console</title>
<style>
:root{color-scheme:dark;background:#0b0d0f;color:#e8ecef;font:16px system-ui,sans-serif}
body{max-width:1050px;margin:32px auto;padding:0 20px} h1{font-size:28px;margin:0}
small,.muted{color:#8e9aa3}.top{display:flex;justify-content:space-between;align-items:center}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:14px;margin:20px 0}
.card{background:#13171b;border:1px solid #283039;border-radius:12px;padding:18px}
.service{display:flex;justify-content:space-between;gap:12px;align-items:center;margin:10px 0}
.ok{color:#8fd694}.bad{color:#ef8b8b} button{background:#242b31;color:#eef;border:1px solid #39434c;
border-radius:7px;padding:7px 11px;cursor:pointer} button:hover{background:#303941}
button.danger{border-color:#7d4444} pre{white-space:pre-wrap;font-size:13px;max-height:320px;overflow:auto}
input{width:75%;padding:10px;background:#0c1013;color:#eee;border:1px solid #39434c;border-radius:7px}
</style></head><body>
<div class="top"><div><h1>3090</h1><small>Operator Console</small></div><div id="health">loading…</div></div>
<div class="grid"><div class="card"><b>SYSTEM</b><pre id="system"></pre></div>
<div class="card"><b>GPU / NETWORK</b><pre id="network"></pre></div></div>
<div class="card"><b>SERVICES</b><div id="services"></div></div>
<div class="card" style="margin-top:14px"><b>SEARCH</b><p><input id="q" placeholder="Search the web…">
<button onclick="search()">Search</button></p><pre id="results"></pre></div>
<div class="card" style="margin-top:14px"><b>DIAGNOSTICS</b>
<p><button onclick="doctor()">Run Doctor</button></p><pre id="diag"></pre></div>
<script>
async function api(path,opt){let r=await fetch(path,opt);let t=await r.text();try{return JSON.parse(t)}catch{return {text:t,ok:r.ok}}}
async function refresh(){let d=await api('/api/status'); health.innerHTML=d.ok?'<span class=ok>● HEALTHY</span>':'<span class=bad>● ATTENTION</span>';
system.textContent=d.system||'';network.textContent=d.network||'';
services.innerHTML=''; for(let s of d.services||[]){let row=document.createElement('div');row.className='service';
row.innerHTML=`<span><b>${s.name}</b><br><small>${s.summary}</small></span><span>
<button onclick="act('${s.id}','restart')">Restart</button> <button onclick="logs('${s.id}')">Logs</button></span>`;services.appendChild(row)}}
async function act(id,a){await api('/api/action',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id,action:a})});refresh()}
async function logs(id){diag.textContent=(await api('/api/logs?id='+id)).text||''}
async function doctor(){diag.textContent='Running…';diag.textContent=(await api('/api/doctor',{method:'POST'})).text||'';refresh()}
async function search(){results.textContent='Searching…';let d=await api('/api/search?q='+encodeURIComponent(q.value));results.textContent=d.text||''}
refresh();setInterval(refresh,5000);
</script></body></html>"""

def run(*args, timeout=25):
    try:
        p=subprocess.run([SERVER,*args],text=True,capture_output=True,timeout=timeout)
        return p.returncode,p.stdout+p.stderr
    except Exception as e:return 1,str(e)

class H(BaseHTTPRequestHandler):
    def send(self,code,body,ctype="application/json"):
        data=body.encode(); self.send_response(code);self.send_header("Content-Type",ctype);self.send_header("Content-Length",str(len(data)));self.end_headers();self.wfile.write(data)
    def log_message(self,*a): pass
    def do_GET(self):
        u=urlparse(self.path)
        if u.path=="/": return self.send(200,HTML,"text/html; charset=utf-8")
        if u.path=="/api/status":
            rc,out=run("discover","--json")
            try:
                d=json.loads(out)
                services=[]
                ok=True
                for s in d.get("services",[]):
                    healthy=bool(s.get("healthy")); ok=ok and (healthy or s.get("id") in ("webterm","console") or s.get("lifecycle")=="missing")
                    services.append({"id":s.get("id"),"name":s.get("name"),"summary":f"{'running' if healthy else 'stopped'} · {s.get('lifecycle','?')}"})
                sysd=d.get("system",{}); gpu=d.get("gpu",{}); net=d.get("tailscale",{})
                return self.send(200,json.dumps({"ok":ok,"services":services,
                    "system":f"OS: {sysd.get('os','')}\nUptime: {sysd.get('uptime','')}\nCPU: {sysd.get('cpu','')}\nMemory used: {round((sysd.get('memory') or {}).get('used',0)/(1024**3),1)} GiB",
                    "network":f"GPU: {gpu.get('name','')}\nVRAM: {round(gpu.get('vram_used_mib',0)/1024,1)} / {round(gpu.get('vram_total_mib',0)/1024,1)} GiB\nTemp: {gpu.get('temperature_c','')}°C\nTailscale: {'connected' if net.get('connected') else 'down'}\nNode: {net.get('name','')}"}))
            except Exception:return self.send(500,json.dumps({"ok":False,"error":out}))
        if u.path=="/api/logs":
            from urllib.parse import parse_qs
            ident=parse_qs(u.query).get("id",[""])[0]; rc,out=run("logs",ident)
            return self.send(200,json.dumps({"text":out}))
        if u.path=="/api/search":
            from urllib.parse import parse_qs
            q=parse_qs(u.query).get("q",[""])[0]; rc,out=run("search",q)
            return self.send(200,json.dumps({"text":out}))
        self.send(404,'{}')
    def do_POST(self):
        if self.path=="/api/doctor":
            rc,out=run("doctor",timeout=35); return self.send(200,json.dumps({"text":out,"ok":rc==0}))
        if self.path=="/api/action":
            n=int(self.headers.get("Content-Length","0")); d=json.loads(self.rfile.read(n) or b"{}")
            if d.get("action") not in ("restart",): return self.send(400,'{"error":"unsupported"}')
            if d.get("id") not in ("ollama","comfy","mercury","searxng","signal"): return self.send(400,'{"error":"unknown service"}')
            rc,out=run(d["action"],d["id"],timeout=35); return self.send(200,json.dumps({"text":out,"ok":rc==0}))
        self.send(404,'{}')

print(f"3090 Operator Console · http://{HOST}:{PORT}")
ThreadingHTTPServer((HOST,PORT),H).serve_forever()
