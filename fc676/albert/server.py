#!/usr/bin/env python3
"""Albert 5: quiet browser surface for the local Future Crash Fabric."""
from __future__ import annotations
import json, mimetypes, os, urllib.request, urllib.error, importlib.util, threading, time, hashlib, re, sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, unquote

ROOT=Path(__file__).resolve().parent
# Installed Albert lives beside Future Crash rather than inside the source tree.
# Prefer the canonical installed Fabric core; fall back to the checkout layout
# for development/tests. This mirrors Signal and keeps both surfaces on one core.
CORE_DIR=Path.home()/".local/share/future-crash-look/core"
if not (CORE_DIR/"endpoint_auth.py").exists():
    CORE_DIR=ROOT.parent/"core"
if str(CORE_DIR) not in sys.path: sys.path.insert(0,str(CORE_DIR))
from endpoint_auth import EndpointAuth
ENDPOINT_AUTH=EndpointAuth()
ENDPOINT_COOKIE="fcl_endpoint"
PENDING_COOKIE="fcl_pending"
ARTIFACT_DIR=Path.home()/".local/share/future-crash-look/albert-artifacts"
ARTIFACT_DIR.mkdir(parents=True,exist_ok=True)
HOST=os.environ.get("ALBERT_HOST","127.0.0.1")
PORT=int(os.environ.get("ALBERT_PORT","7330"))
NODE=os.environ.get("FABRIC_NODE_URL","http://127.0.0.1:7332").rstrip("/")
ALL_CLASSICAL="https://allclassical.streamguys1.com/ac128kmp3"
CLASSIC_ARTS="https://www.classicartsshowcase.org/watch-classic-arts-showcase/"
CLASSIC_ARTS_STREAM="https://classicarts.global.ssl.fastly.net/live/cas/master_3000k.m3u8"

_LO_ENGINE=None
_LO_LOCK=threading.Lock()
_SESSIONS={}
_SESSION_LOCK=threading.Lock()
_SESSION_TTL=6*3600

def _lo_engine_path():
    candidates=[
        Path.home()/".local/share/look/lo_engine.py",
        ROOT.parent/"look/lo_engine.py",
    ]
    for path in candidates:
        if path.is_file():
            return path
    raise RuntimeError("shared LO engine not installed")

def _load_lo_engine():
    global _LO_ENGINE
    with _LO_LOCK:
        if _LO_ENGINE is not None:
            return _LO_ENGINE
        path=_lo_engine_path()
        spec=importlib.util.spec_from_file_location("albert_shared_lo_engine",path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"cannot load shared LO engine: {path}")
        module=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _LO_ENGINE=module
        return module

def _session_history(session_id):
    if not session_id:
        return []
    now=time.time()
    with _SESSION_LOCK:
        for key,(stamp,_rows) in list(_SESSIONS.items()):
            if now-stamp > _SESSION_TTL:
                _SESSIONS.pop(key,None)
        row=_SESSIONS.get(session_id)
        return list(row[1]) if row else []

def _session_append(session_id,user_text,assistant_text):
    if not session_id:
        return
    with _SESSION_LOCK:
        rows=list(_SESSIONS.get(session_id,(0,[]))[1])
        if user_text:
            rows.append({"role":"user","content":str(user_text)[:12000]})
        if assistant_text:
            rows.append({"role":"assistant","content":str(assistant_text)[:12000]})
        _SESSIONS[session_id]=(time.time(),rows[-12:])

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


def _needs_live_search(text):
    low=str(text or '').casefold()
    return any(token in low for token in ('headline','headlines','news','latest','today','current events','what happened'))

def _looks_like_tool_plumbing(text):
    low=str(text or "").casefold()
    return ("### function call" in low or "<tool_call>" in low or
            bool(re.search(r"```(?:json)?\s*\{\s*[\"'](?:name|tool)[\"']\s*:", str(text or ""), re.I)))

def cognition_json(text, session="", selected_paths=None):
    """Run the same native LO engine used by Signal, without crossing Signal auth."""
    sid=(session or "albert")[:120]
    engine=_load_lo_engine()
    result=engine.chat_once(
        text,
        profile="workspace",
        workspace=str(Path.home()),
        history=_session_history(sid),
        selected_paths=list(selected_paths or []),
        force_search=False,
        interface_context=(
            "INTERFACE: Albert quiet paper browser surface. Answer normally and truthfully in concise prose suitable for a fold. "
            "Albert owns presentation; do not claim a UI action happened unless the tool result says it happened. "
            "Effects are local by default and compute may float across Fabric."
        ),
    )
    answer=str(result.get("text") or "").strip()
    if not answer:
        raise RuntimeError("shared LO engine returned no answer")
    if _looks_like_tool_plumbing(answer):
        # Tool protocol is machinery, never paper. A model that narrates a call
        # instead of executing it has not completed the user's request.
        raise RuntimeError("cognition returned unexecuted tool protocol")
    _session_append(sid,text,answer)
    return {"text":answer,"lo_events":list(result.get("events") or []),"provenance":result.get("provenance")}

def action(text, session="", context=None):
    context=context or {}
    q=" ".join(str(text or "").strip().split()); low=q.casefold().strip(" .!?")
    if low in {"classics","classical","classical music","play classics","play classical","put on classical music"} or "all classical" in low:
        return {"type":"audio","title":"All Classical Radio","subtitle":"Portland · live","meta":"media.play · this endpoint","badge":"live","kind":"things","src":ALL_CLASSICAL,"note":"Fabric built-in · classics","pipeline":{"intent":"media.play","selector":"stream:all-classical","target":"origin endpoint","effect":"local"}}
    if low in {"arts","showcase","play arts"} or "classic arts" in low or "arts showcase" in low:
        return {"type":"video","title":"Classic Arts Showcase","meta":"media.play · this endpoint","badge":"live","kind":"things","src":CLASSIC_ARTS_STREAM,"embed":CLASSIC_ARTS,"external":CLASSIC_ARTS,"text":"24-hour classic arts stream. Direct HLS when this browser supports it; fitted official-page fallback otherwise.","pipeline":{"intent":"media.play","selector":"stream:classic-arts-showcase","target":"origin endpoint","preferred":"direct HLS","fallback":"official feed"}}
    if low in {"fabric","nodes","show nodes","what nodes are online"}:
        try:
            data=node_json('/v1/nodes'); peers=data.get('peers') or []
            names=[str((data.get('self') or {}).get('name') or 'local')]+[str(x.get('name') or x.get('hostname') or 'peer') for x in peers]
            return {"type":"answer","title":"Fabric","meta":"node discovery","badge":f"{len(names)} nodes","kind":"things","text":"Available: "+", ".join(names),"pipeline":{"source":"/v1/nodes","effect":"read"}}
        except Exception as exc:
            return {"type":"answer","title":"Fabric","meta":"node discovery","badge":"offline","text":f"Unified Node is not reachable: {exc}"}
    # The shared LO core owns intent routing. In particular, "play a game" is
    # not media merely because it starts with the word play.
    try:
        shared_intent=_load_lo_engine().route_intent(q)
    except Exception:
        shared_intent="general"

    # Media language already has a mature deterministic bridge. Ask the node to
    # prepare rather than play so Albert remains the owner of browser effects.
    if shared_intent!="games" and low.startswith(('play ','put on ','shuffle ','queue ')):
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
    # Anything not handled by a deterministic fast path goes to the *same* LO
    # cognition/tool plane used elsewhere. Albert must never stop at a fake
    # "understood" receipt when Fabric can actually reason, search or use tools.
    try:
        artifact_ids=[str(x) for x in (context.get("artifacts") or []) if str(x).strip()]
        selected=[]
        for aid in artifact_ids[:8]:
            safe=re.sub(r"[^a-f0-9]","",aid.lower())[:64]
            matches=list(ARTIFACT_DIR.glob(safe+"*")) if safe else []
            if matches:
                selected.append(str(matches[0]))
        reply=cognition_json(q, session=session, selected_paths=selected)
        text=str(reply.get("text") or "").strip()
        if not text:
            raise RuntimeError(reply.get("error") or "empty cognition response")
        events=reply.get("lo_events") or []
        tool_names=[]
        for event in events:
            if isinstance(event,dict):
                name=event.get("tool")
                if name and name not in tool_names:
                    tool_names.append(str(name))
        pipeline={"cognition":"shared LO engine","session":session or "albert"}
        if tool_names:
            pipeline["tools"]=" · ".join(tool_names)
        is_game="game_action" in tool_names
        return {
            "type":"answer",
            "title":"LOOK Games" if is_game else "Albert",
            "meta":"",
            "badge":"ready" if is_game else ("grounded" if tool_names else "answer"),
            "kind":"things",
            "text":text,
            "pipeline":pipeline,
        }
    except Exception as exc:
        detail=" ".join(str(exc).split())[:360]
        low=detail.casefold()
        if "search" in low or "searx" in low:
            meta="Live search unavailable"; badge="search offline"
            message="I can reach LO, but the live web-search edge failed for this request. Nothing was invented."
        elif "fabric inference" in low or "inference" in low or "model" in low:
            meta="Inference unavailable"; badge="brain offline"
            message="Albert reached the cognition engine, but no inference worker completed this request."
        elif "lo engine" in low or "look core" in low or "not installed" in low:
            meta="LO engine unavailable"; badge="engine offline"
            message="Albert is running, but its installed LO engine could not be loaded."
        else:
            meta="Cognition request failed"; badge="not completed"
            message="Albert reached the cognition path, but this request did not complete. Nothing was invented."
        return {
            "type":"answer", "title":"Albert", "meta":meta, "badge":badge, "kind":"things",
            "text":message,
            "pipeline":{"cognition":"shared native LO engine","error":detail},
        }

class Handler(BaseHTTPRequestHandler):
    server_version='Albert/1.2.4'
    def log_message(self,*_): pass
    def send_json(self,code,obj,headers=None):
        raw=json.dumps(obj,ensure_ascii=False).encode(); self.send_response(code); self.send_header('Content-Type','application/json; charset=utf-8'); self.send_header('Content-Length',str(len(raw)));
        for k,v in (headers or []): self.send_header(k,v)
        self.end_headers(); self.wfile.write(raw)
    def _cookie(self,name):
        raw=str(self.headers.get("Cookie") or "")
        for bit in raw.split(";"):
            if "=" in bit:
                k,v=bit.strip().split("=",1)
                if k==name:return v
        return ""
    def _secure_cookie(self):
        host=str(self.headers.get("Host") or "").split(":",1)[0].casefold(); proto=str(self.headers.get("X-Forwarded-Proto") or "").casefold()
        return proto=="https" or host.endswith(".ts.net")
    def _set_cookie(self,name,value,max_age):
        bits=[f"{name}={value}","Path=/","HttpOnly","SameSite=Strict",f"Max-Age={int(max_age)}"]
        if self._secure_cookie():bits.append("Secure")
        return ("Set-Cookie","; ".join(bits))
    def _endpoint(self): return ENDPOINT_AUTH.verify(self._cookie(ENDPOINT_COOKIE))
    def _require_endpoint(self,scope="lo.use"):
        ep=self._endpoint()
        if not ep: self.send_json(401,{"ok":False,"error":"Fabric endpoint authorization required"}); return None
        if scope and scope not in set(ep.get("scopes") or []): self.send_json(403,{"ok":False,"error":f"Fabric endpoint lacks scope: {scope}"}); return None
        return ep
    def _auth_status(self):
        ep=self._endpoint()
        if ep:return self.send_json(200,{"authorized":True,"endpoint":ep})
        pending=self._cookie(PENDING_COOKIE)
        if pending:
            row=ENDPOINT_AUTH.pending_status(pending)
            if row and row.get("approved"):
                issued=ENDPOINT_AUTH.redeem_pending(pending,label=str(self.headers.get("User-Agent") or "Browser")[:80])
                if issued:
                    return self.send_json(200,{"authorized":True,"endpoint":{k:v for k,v in issued.items() if k!="token"}},[self._set_cookie(ENDPOINT_COOKIE,issued["token"],31536000 if issued.get("mode")=="trust" else 43200),self._set_cookie(PENDING_COOKIE,"",0)])
            if row:return self.send_json(200,{"authorized":False,"pending":{k:v for k,v in row.items() if k!="id"}})
        row=ENDPOINT_AUTH.request(user_agent=str(self.headers.get("User-Agent") or ""),remote=str(self.client_address[0]))
        return self.send_json(200,{"authorized":False,"pending":{k:v for k,v in row.items() if k!="id"}},[self._set_cookie(PENDING_COOKIE,row["id"],300)])
    def do_GET(self):
        path=urlparse(self.path).path
        if path=='/api/auth/status': return self._auth_status()
        if path in {'/health','/v1/health'}: return self.send_json(200,{"ok":True,"surface":"albert","version":"1.2.3","fabric":NODE})
        if path in {'/v1/actions','/api/capabilities'}:
            if not self._require_endpoint('lo.use'): return
            try: caps=node_json('/v1/capabilities')
            except Exception: caps={}
            return self.send_json(200,{"schema":"fabric-action-registry-v1","surface":"albert","tools":TOOLS,"node_capabilities":caps})
        if path=='/api/fabric':
            if not self._require_endpoint('lo.use'): return
            try: return self.send_json(200,{"ok":True,"nodes":node_json('/v1/nodes'),"capabilities":node_json('/v1/capabilities')})
            except Exception as exc: return self.send_json(503,{"ok":False,"error":str(exc)})
        if path=='/v1/lights':
            if not self._require_endpoint('lo.use'): return
            try: return self.send_json(200,node_json('/v1/lights'))
            except Exception as exc: return self.send_json(503,{"pulse":0,"light":None,"error":str(exc)})
        if path.startswith('/v1/artifacts/'):
            if not self._require_endpoint('lo.use'): return
            aid=re.sub(r'[^a-f0-9]','',path.rsplit('/',1)[-1].lower())[:64]
            matches=list(ARTIFACT_DIR.glob(aid+'*')) if aid else []
            if not matches: return self.send_error(404)
            target=matches[0]; data=target.read_bytes()
            self.send_response(200); self.send_header('Content-Type',mimetypes.guess_type(target.name)[0] or 'application/octet-stream'); self.send_header('Cache-Control','private, max-age=3600'); self.send_header('Content-Length',str(len(data))); self.end_headers(); self.wfile.write(data); return
        rel='index.html' if path in {'/','/index.html'} else path.lstrip('/')
        target=(ROOT/rel).resolve()
        if ROOT not in target.parents and target!=ROOT: return self.send_error(403)
        if not target.is_file(): return self.send_error(404)
        data=target.read_bytes(); self.send_response(200); self.send_header('Content-Type',mimetypes.guess_type(target.name)[0] or 'application/octet-stream'); self.send_header('Cache-Control','no-cache'); self.send_header('Content-Length',str(len(data))); self.end_headers(); self.wfile.write(data)
    def do_POST(self):
        path=urlparse(self.path).path
        if path=='/api/endpoint/poll':
            ep=self._require_endpoint('lo.use')
            if not ep:return
            try:
                n=int(self.headers.get('Content-Length') or 0); d=json.loads(self.rfile.read(min(n,65536)) or b'{}')
                label=str(d.get('label') or ep.get('label') or 'Browser')[:80]
                caps=d.get('capabilities') or ['display.output','audio.output','audio.speak','media.play','input.text']
                node_json('/v1/endpoints/presence',{'endpoint_id':ep.get('endpoint_id'),'label':label,'capabilities':caps,'surface':'albert','metadata':d.get('metadata') or {}},timeout=1.5)
                value=node_json('/v1/endpoints/poll',{'endpoint_id':ep.get('endpoint_id')},timeout=1.5)
                return self.send_json(200,value or {'actions':[]})
            except Exception as exc:return self.send_json(502,{'ok':False,'error':str(exc),'actions':[]})
        if path=='/api/endpoint/receipt':
            ep=self._require_endpoint('lo.use')
            if not ep:return
            try:
                n=int(self.headers.get('Content-Length') or 0); d=json.loads(self.rfile.read(min(n,16384)) or b'{}')
                value=node_json('/v1/endpoints/receipt',{'endpoint_id':ep.get('endpoint_id'),'action_id':d.get('action_id'),'state':d.get('state'),'detail':d.get('detail') or ''},timeout=1.5)
                return self.send_json(200,value or {'ok':True})
            except Exception as exc:return self.send_json(502,{'ok':False,'error':str(exc)})
        if path in {'/v1/artifacts','/v1/actions'} and not self._require_endpoint('lo.use'): return
        if path=='/v1/artifacts':
            try:
                n=int(self.headers.get('Content-Length') or 0)
                if n<=0 or n>32*1024*1024: return self.send_json(413,{"ok":False,"error":"artifact must be 1 byte to 32 MiB"})
                data=self.rfile.read(n); digest=hashlib.sha256(data).hexdigest()
                name=unquote(str(self.headers.get('X-Filename') or 'object')).replace('\x00','')
                suffix=Path(name).suffix[:16]
                target=ARTIFACT_DIR/(digest+suffix)
                if not target.exists(): target.write_bytes(data)
                return self.send_json(200,{"ok":True,"id":digest,"uri":"artifact://sha256/"+digest,"name":name,"mime":self.headers.get('Content-Type') or mimetypes.guess_type(name)[0] or 'application/octet-stream',"size":len(data),"preview":"/v1/artifacts/"+digest})
            except Exception as exc: return self.send_json(400,{"ok":False,"error":str(exc)})
        if path!='/v1/actions': return self.send_error(404)
        try:
            n=int(self.headers.get('Content-Length') or 0); raw=self.rfile.read(min(n,262144)); payload=json.loads(raw or b'{}'); text=((payload.get('input') or {}).get('text') or payload.get('text') or '')
            context=payload.get('context') or {}
            session=str(payload.get("session") or context.get("session") or "").strip()[:120]
            return self.send_json(200,action(text,session=session,context=context))
        except Exception as exc: return self.send_json(400,{"ok":False,"error":str(exc)})

if __name__=='__main__':
    print(f'Albert 5 · http://{HOST}:{PORT} · Fabric {NODE} · cognition native LO',flush=True)
    ThreadingHTTPServer((HOST,PORT),Handler).serve_forever()
