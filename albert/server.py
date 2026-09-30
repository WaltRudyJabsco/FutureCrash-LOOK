#!/usr/bin/env python3
"""Albert 5: quiet browser surface for the local Future Crash Fabric."""
from __future__ import annotations
import json, mimetypes, os, urllib.request, urllib.error, importlib.util, threading, time, hashlib, re, sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, unquote, urlencode, parse_qs, quote

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
_SESSION_TTL=30*24*3600
THREAD_FILE=Path.home()/'.local/share/future-crash-look/albert-threads.json'
SAVED_FILE=Path.home()/'.local/share/future-crash-look/albert-saved.json'
THREAD_FILE.parent.mkdir(parents=True,exist_ok=True)

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

def _load_threads():
    try:
        raw=json.loads(THREAD_FILE.read_text()) if THREAD_FILE.exists() else {}
        return {str(k):(float(v.get("stamp") or 0),list(v.get("rows") or [])) for k,v in raw.items() if isinstance(v,dict)}
    except Exception:
        return {}

def _save_threads():
    payload={k:{"stamp":stamp,"rows":rows} for k,(stamp,rows) in _SESSIONS.items()}
    tmp=THREAD_FILE.with_name(THREAD_FILE.name+f'.{os.getpid()}.tmp')
    tmp.write_text(json.dumps(payload,ensure_ascii=False,indent=2))
    tmp.replace(THREAD_FILE)

_SESSIONS.update(_load_threads())

def _read_saved():
    try:
        rows=json.loads(SAVED_FILE.read_text()) if SAVED_FILE.exists() else []
        return rows if isinstance(rows,list) else []
    except Exception:
        return []

def _write_saved(rows):
    SAVED_FILE.parent.mkdir(parents=True,exist_ok=True)
    clean=list(rows or [])[-48:]
    tmp=SAVED_FILE.with_name(SAVED_FILE.name+f'.{os.getpid()}.{threading.get_ident()}.tmp')
    tmp.write_text(json.dumps(clean,ensure_ascii=False,indent=2))
    tmp.replace(SAVED_FILE)

def _canonical_saved_title(item):
    title=str(item.get('title') or '').strip()
    kind=str(item.get('type') or '').casefold()
    prompt=str(item.get('prompt') or '').strip()
    if kind=='places':
        return title if title and title!='Albert' else 'Places'
    if 'weather' in prompt.casefold():
        # The result title is preferred when the weather edge supplied a place.
        if title and title.casefold() not in {'albert','the weather','the weather again','weather again'}:
            return title
        return 'Weather'
    return title or (prompt[:48].rstrip(' ?!.') if prompt else 'Saved item')

def _normalize_saved(item):
    row=dict(item or {})
    row['id']=str(row.get('id') or hashlib.sha256(json.dumps(row,sort_keys=True,default=str).encode()).hexdigest()[:16])[:80]
    row['title']=_canonical_saved_title(row)[:100]
    row['pinned']=bool(row.get('pinned'))
    row['saved_at']=float(row.get('saved_at') or time.time())
    # Saved objects retain the request needed to refresh dynamic information.
    if row.get('prompt'): row['prompt']=str(row['prompt'])[:12000]
    return row

def saved_upsert(item):
    row=_normalize_saved(item)
    rows=_read_saved(); rows=[x for x in rows if str(x.get('id'))!=row['id']]; rows.append(row); _write_saved(rows)
    return row

def saved_patch(item_id,changes):
    rows=_read_saved(); found=None
    for i,row in enumerate(rows):
        if str(row.get('id'))==str(item_id):
            nxt=dict(row)
            if 'title' in changes: nxt['title']=str(changes.get('title') or '').strip()[:100] or row.get('title') or 'Saved item'
            if 'pinned' in changes: nxt['pinned']=bool(changes.get('pinned'))
            rows[i]=_normalize_saved(nxt); found=rows[i]; break
    if found: _write_saved(rows)
    return found

def saved_delete(item_id):
    rows=_read_saved(); nxt=[x for x in rows if str(x.get('id'))!=str(item_id)]
    if len(nxt)==len(rows): return False
    _write_saved(nxt); return True

def _place_query(text):
    q=' '.join(str(text or '').split())
    low=q.casefold()
    if low.startswith(('map ','show me on a map ','where is ','where are ')) or any(x in low for x in (' on a map',' map of ',' near ')):
        for prefix in ('show me on a map ','where is ','where are ','map '):
            if low.startswith(prefix): return q[len(prefix):].strip(' ?.')
        return q
    return ''

def places_search(query,limit=6):
    params=urlencode({'q':query,'format':'jsonv2','limit':max(1,min(int(limit),8)),'addressdetails':1})
    req=urllib.request.Request('https://nominatim.openstreetmap.org/search?'+params,headers={'User-Agent':'FutureCrash-Albert/7.6.2 (local personal assistant)','Accept':'application/json'})
    with urllib.request.urlopen(req,timeout=5.0) as r: raw=json.loads(r.read().decode())
    places=[]
    for x in raw:
        try: lat=float(x['lat']); lon=float(x['lon'])
        except Exception: continue
        label=str(x.get('name') or str(x.get('display_name') or '').split(',')[0] or 'Place')[:100]
        places.append({'name':label,'lat':lat,'lon':lon,'address':str(x.get('display_name') or label)[:300],'kind':str(x.get('type') or x.get('category') or 'place')[:50]})
    return places

def places_result(query):
    places=places_search(query)
    if not places: return None
    return {'type':'places','title':query[:80].title(),'meta':'OpenStreetMap · Nominatim','badge':'verified','kind':'things','text':f"{len(places)} place"+('' if len(places)==1 else 's')+' found.','places':places,'evidence':[{'class':'PLACES','source':'OpenStreetMap · Nominatim','confidence':'DIRECT','verified':True}],'sources':['OpenStreetMap contributors · Nominatim'],'prompt':'map '+query}

def _session_history(session_id):
    session_id=str(session_id or 'main')[:120]
    now=time.time()
    with _SESSION_LOCK:
        expired=[key for key,(stamp,_rows) in _SESSIONS.items() if now-stamp > _SESSION_TTL]
        for key in expired: _SESSIONS.pop(key,None)
        if expired: _save_threads()
        row=_SESSIONS.get(session_id)
        return list(row[1]) if row else []

def _session_append(session_id,user_text,assistant_text):
    session_id=str(session_id or 'main')[:120]
    with _SESSION_LOCK:
        rows=list(_SESSIONS.get(session_id,(0,[]))[1])
        if user_text: rows.append({"role":"user","content":str(user_text)[:12000]})
        if assistant_text: rows.append({"role":"assistant","content":str(assistant_text)[:12000]})
        _SESSIONS[session_id]=(time.time(),rows[-40:])
        _save_threads()

def _trust_evidence(reply):
    receipts=list(reply.get("receipts") or [])
    if receipts:
        out=[]
        for r in receipts:
            edge=str(r.get("edge") or "SOURCE").upper()
            out.append({"class":edge,"source":str(r.get("source") or edge),"confidence":str(r.get("confidence") or "DIRECT"),"verified":edge not in {"MODEL","INFER"}})
        return out
    p=reply.get("provenance") or {}
    edge=str(p.get("edge") or "MODEL").upper()
    return [{"class":edge,"source":str(p.get("source") or "model"),"confidence":str(p.get("confidence") or "INFERRED"),"verified":False}]

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


def _proxy_media_item(handler,node,item_id,*,head=False):
    """Browser-safe range proxy for one prepared Fabric media item."""
    query="?node="+quote(str(node or ""),safe="")+"&id="+quote(str(item_id or ""),safe="")
    req=urllib.request.Request(NODE+"/v1/media/item"+query,method="HEAD" if head else "GET")
    if handler.headers.get("Range"):
        req.add_header("Range",handler.headers.get("Range"))
    try:
        with urllib.request.urlopen(req,timeout=12.0) as r:
            handler.send_response(getattr(r,"status",200))
            for key in ("Content-Type","Content-Length","Accept-Ranges","Content-Range","Cache-Control"):
                value=r.headers.get(key)
                if value: handler.send_header(key,value)
            handler.end_headers()
            if not head:
                while True:
                    chunk=r.read(256*1024)
                    if not chunk: break
                    handler.wfile.write(chunk)
    except urllib.error.HTTPError as exc:
        handler.send_response(exc.code); handler.send_header("Content-Length","0"); handler.end_headers()
    except Exception:
        handler.send_response(502); handler.send_header("Content-Length","0"); handler.end_headers()


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
    return {"text":answer,"lo_events":list(result.get("events") or []),"provenance":result.get("provenance"),"receipts":list(result.get("receipts") or []),"route":result.get("route")}

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
    place_q=_place_query(q)
    if place_q:
        try:
            found=places_result(place_q)
            if found: return found
        except Exception:
            # Provider failure falls through to cognition; never fabricate coordinates.
            pass

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
            state=prepared.get('prepared') or prepared.get('session') or prepared
            queue=(state.get('queue') if isinstance(state,dict) else None) or []
            if queue:
                first=queue[0]; title=first.get('title') or first.get('name') or query
                media_type=str(first.get('media_type') or '').casefold()
                item_id=str(first.get('id') or first.get('digest') or '')
                media_node=str(first.get('node') or prepared.get('node') or '')
                if item_id:
                    src='/v1/media/item?'+urlencode({'node':media_node,'id':item_id})
                    result_type='video' if media_type.startswith('video/') else 'audio'
                    subtitle=' · '.join(x for x in (str(first.get('artist') or ''),str(first.get('album') or '')) if x)
                    return {"type":result_type,"title":title,"subtitle":subtitle,"meta":f"media.play · {len(queue)} item(s)","badge":"live","kind":"things","src":src,"note":f"Fabric media · {len(queue)} resolved item(s)","pipeline":{"intent":"media.play","source":"Fabric media catalog","target":"origin endpoint","effect":"browser playback"}}
                return {"type":"answer","title":title,"meta":f"media.prepare · {len(queue)} item(s)","badge":"prepared","kind":"things","text":"Fabric resolved the request, but this item has no stream identity for browser playback.","pipeline":{"intent":"media.play","source":"Fabric media catalog","target":"origin endpoint"}}
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
        evidence=_trust_evidence(reply)
        return {
            "type":"answer",
            "title":"LOOK Games" if is_game else "Albert",
            "meta":"",
            "badge":"ready" if is_game else ("verified" if any(x.get("verified") for x in evidence) else "inference"),
            "kind":"things",
            "text":text,
            "evidence":evidence,
            "signal":{"mode":"response","seed":hashlib.sha256(text.encode()).hexdigest()[:24]},
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
    server_version='Albert/1.4.0'
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
        if path in {'/health','/v1/health'}: return self.send_json(200,{"ok":True,"surface":"albert","version":"1.4.0","fabric":NODE})
        if path=='/api/saved':
            if not self._require_endpoint('lo.use'): return
            return self.send_json(200,{'ok':True,'items':_read_saved()})
        if path=='/api/thread':
            if not self._require_endpoint('lo.use'): return
            from urllib.parse import parse_qs
            sid=str(parse_qs(urlparse(self.path).query).get('session',['main'])[0] or 'main')[:120]
            return self.send_json(200,{"ok":True,"session":sid,"turns":_session_history(sid)})
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
        if path=='/v1/media/item':
            if not self._require_endpoint('lo.use'): return
            params=parse_qs(urlparse(self.path).query)
            node=str(params.get('node',[''])[0] or '')
            item_id=str(params.get('id',[''])[0] or '')
            if not item_id: return self.send_json(400,{'ok':False,'error':'media item id required'})
            return _proxy_media_item(self,node,item_id)
        rel='index.html' if path in {'/','/index.html'} else path.lstrip('/')
        target=(ROOT/rel).resolve()
        if ROOT not in target.parents and target!=ROOT: return self.send_error(403)
        if not target.is_file(): return self.send_error(404)
        data=target.read_bytes(); self.send_response(200); self.send_header('Content-Type',mimetypes.guess_type(target.name)[0] or 'application/octet-stream'); self.send_header('Cache-Control','no-cache'); self.send_header('Content-Length',str(len(data))); self.end_headers(); self.wfile.write(data)
    def do_POST(self):
        path=urlparse(self.path).path
        if path=='/api/saved':
            if not self._require_endpoint('lo.use'): return
            try:
                n=int(self.headers.get('Content-Length') or 0); d=json.loads(self.rfile.read(min(n,262144)) or b'{}')
                op=str(d.get('op') or 'save')
                if op=='save': return self.send_json(200,{'ok':True,'item':saved_upsert(d.get('item') or {})})
                if op=='patch':
                    row=saved_patch(d.get('id'),d.get('changes') or {})
                    return self.send_json(200 if row else 404,{'ok':bool(row),'item':row})
                if op=='delete': return self.send_json(200,{'ok':saved_delete(d.get('id'))})
                return self.send_json(400,{'ok':False,'error':'unknown saved operation'})
            except Exception as exc: return self.send_json(400,{'ok':False,'error':str(exc)})
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
