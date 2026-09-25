#!/usr/bin/env python3
"""Albert 5: quiet browser surface for the local Future Crash Fabric."""
from __future__ import annotations
import json, mimetypes, os, urllib.request, urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT=Path(__file__).resolve().parent
HOST=os.environ.get("ALBERT_HOST","127.0.0.1")
PORT=int(os.environ.get("ALBERT_PORT","7330"))
NODE=os.environ.get("FABRIC_NODE_URL","http://127.0.0.1:7332").rstrip("/")
ALL_CLASSICAL="https://allclassical.streamguys1.com/ac128kmp3"
CLASSIC_ARTS="https://www.classicartsshowcase.org/watch-classic-arts-showcase/"
TOOLS=[
 {"name":"media.play","does":"Play or prepare media","risk":"local_effect"},
 {"name":"media.control","does":"Control the selected media output","risk":"local_effect"},
 {"name":"files.search","does":"Find objects across Fabric nodes","risk":"read"},
 {"name":"web.search","does":"Search through an available web provider","risk":"read"},
 {"name":"mail.search","does":"Find mail through an available adapter","risk":"read"},
 {"name":"mail.send","does":"Send mail through an available adapter","risk":"external_effect"},
 {"name":"calendar.search","does":"Find calendar events","risk":"read"},
 {"name":"calendar.create","does":"Create a calendar event","risk":"external_effect"},
 {"name":"contacts.search","does":"Resolve a person","risk":"read"},
 {"name":"maps.route","does":"Build a route through an available maps provider","risk":"local_effect"},
 {"name":"watch.create","does":"Create a recurring or conditional watch","risk":"external_effect"},
]

def node_json(path, payload=None, timeout=1.25):
    req=urllib.request.Request(NODE+path, data=(json.dumps(payload).encode() if payload is not None else None), headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(req,timeout=timeout) as r: return json.loads(r.read().decode())

def action(text):
    q=" ".join(str(text or "").strip().split()); low=q.casefold().strip(" .!?")
    if low in {"classics","classical","classical music","play classics","play classical","put on classical music"} or "all classical" in low:
        return {"type":"audio","title":"All Classical Radio","subtitle":"Portland · live","meta":"media.play · this endpoint","badge":"live","kind":"things","src":ALL_CLASSICAL,"note":"Fabric built-in · classics","pipeline":{"intent":"media.play","selector":"stream:all-classical","target":"origin endpoint","effect":"local"}}
    if low in {"arts","showcase","play arts"} or "classic arts" in low or "arts showcase" in low:
        return {"type":"video","title":"Classic Arts Showcase","meta":"media.play · this endpoint","badge":"live","kind":"things","embed":CLASSIC_ARTS,"external":CLASSIC_ARTS,"text":"24-hour classic arts stream via the official web feed.","pipeline":{"intent":"media.play","selector":"stream:classic-arts-showcase","target":"origin endpoint","fallback":"official feed"}}
    if low in {"fabric","nodes","show nodes","what nodes are online"}:
        try:
            data=node_json('/v1/nodes'); peers=data.get('peers') or []
            names=[str((data.get('self') or {}).get('name') or 'local')]+[str(x.get('name') or x.get('hostname') or 'peer') for x in peers]
            return {"type":"answer","title":"Fabric","meta":"node discovery","badge":f"{len(names)} nodes","kind":"things","text":"Available: "+", ".join(names),"pipeline":{"source":"/v1/nodes","effect":"read"}}
        except Exception as exc:
            return {"type":"answer","title":"Fabric","meta":"node discovery","badge":"offline","text":f"Unified Node is not reachable: {exc}"}
    # Media language already has a mature deterministic bridge. Ask the node to
    # prepare rather than play so Albert remains the owner of browser effects.
    if low.startswith(('play ','put on ','shuffle ','queue ')):
        query=q
        for prefix in ('please ','play ','put on ','shuffle ','queue '):
            if query.casefold().startswith(prefix): query=query[len(prefix):].strip(); break
        try:
            prepared=node_json('/v1/media/route',{"operation":"prepare","query":query},timeout=8.0)
            state=prepared.get('prepared') or prepared.get('session') or prepared.get('state') or prepared
            queue=(state.get('queue') if isinstance(state,dict) else None) or []
            if queue:
                first=queue[0]; title=first.get('title') or first.get('name') or query
                return {"type":"answer","title":title,"meta":f"media.prepare · {len(queue)} item(s)","badge":"prepared","kind":"things","text":"Fabric resolved the request without stealing playback from this browser endpoint.","pipeline":{"intent":"media.play","source":"Fabric media catalog","target":"origin endpoint","next":"browser playback adapter"}}
        except Exception:
            pass
    # Until additional adapters land, expose the interpretation boundary instead
    # of pretending an unavailable mail/calendar/maps action happened.
    family='action'
    for key,name in [('mail','mail.*'),('email','mail.*'),('calendar','calendar.*'),('meeting','calendar.*'),('map','maps.*'),('direction','maps.*'),('route','maps.*'),('file','files.*'),('document','files.*'),('watch','watch.*')]:
        if key in low: family=name; break
    return {"type":"answer","title":"Albert","meta":"Fabric cognition handoff","badge":"understood","kind":"things","text":f"I understand the request: “{q}”. The matching capability family is {family}; Albert will execute it when that adapter is available rather than inventing a result.","pipeline":{"understand":"natural language","discover":family,"execute":"exact tool call","trust":"ask only when ambiguity or consequence matters"}}

class Handler(BaseHTTPRequestHandler):
    server_version='Albert/1.0.0'
    def log_message(self,*_): pass
    def send_json(self,code,obj):
        raw=json.dumps(obj,ensure_ascii=False).encode(); self.send_response(code); self.send_header('Content-Type','application/json; charset=utf-8'); self.send_header('Content-Length',str(len(raw))); self.end_headers(); self.wfile.write(raw)
    def do_GET(self):
        path=urlparse(self.path).path
        if path in {'/health','/v1/health'}: return self.send_json(200,{"ok":True,"surface":"albert","version":"1.0.0","fabric":NODE})
        if path in {'/v1/actions','/api/capabilities'}:
            try: caps=node_json('/v1/capabilities')
            except Exception: caps={}
            return self.send_json(200,{"schema":"fabric-action-registry-v1","surface":"albert","tools":TOOLS,"node_capabilities":caps})
        if path=='/api/fabric':
            try: return self.send_json(200,{"ok":True,"nodes":node_json('/v1/nodes'),"capabilities":node_json('/v1/capabilities')})
            except Exception as exc: return self.send_json(503,{"ok":False,"error":str(exc)})
        rel='index.html' if path in {'/','/index.html'} else path.lstrip('/')
        target=(ROOT/rel).resolve()
        if ROOT not in target.parents and target!=ROOT: return self.send_error(403)
        if not target.is_file(): return self.send_error(404)
        data=target.read_bytes(); self.send_response(200); self.send_header('Content-Type',mimetypes.guess_type(target.name)[0] or 'application/octet-stream'); self.send_header('Cache-Control','no-cache'); self.send_header('Content-Length',str(len(data))); self.end_headers(); self.wfile.write(data)
    def do_POST(self):
        if urlparse(self.path).path!='/v1/actions': return self.send_error(404)
        try:
            n=int(self.headers.get('Content-Length') or 0); raw=self.rfile.read(min(n,262144)); payload=json.loads(raw or b'{}'); text=((payload.get('input') or {}).get('text') or payload.get('text') or '')
            return self.send_json(200,action(text))
        except Exception as exc: return self.send_json(400,{"ok":False,"error":str(exc)})

if __name__=='__main__':
    print(f'Albert 5 · http://{HOST}:{PORT} · Fabric {NODE}',flush=True)
    ThreadingHTTPServer((HOST,PORT),Handler).serve_forever()
