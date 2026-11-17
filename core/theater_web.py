"""Guest-only Theater listener. Administration stays behind Fabric authentication."""
import json
import time
import threading
import urllib.parse
import urllib.error
from http.cookies import SimpleCookie, CookieError
from http.server import BaseHTTPRequestHandler
try:from . import theater
except ImportError:import theater

_RATE={}
_RATE_LOCK=threading.Lock()


class Guest(BaseHTTPRequestHandler):
    def log_message(self,*args):pass  # Admission codes must not enter access logs.

    def reply(self,status,value,ctype='application/json',cookie=None,head=False):
        data=value.encode() if isinstance(value,str) else json.dumps(value).encode()
        self.send_response(status)
        self.send_header('Content-Type',ctype);self.send_header('Content-Length',str(len(data)))
        self.send_header('Cache-Control','no-store');self.send_header('Referrer-Policy','no-referrer')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; media-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        if cookie:self.send_header('Set-Cookie',cookie)
        self.end_headers()
        if not head:self.wfile.write(data)

    def code(self):
        cookie=SimpleCookie()
        try:cookie.load(self.headers.get('Cookie',''))
        except CookieError:return None
        return cookie[theater.COOKIE].value if theater.COOKIE in cookie else None

    def do_POST(self):
        if self.path!='/admit':return self.reply(404,{'error':'Unknown Theater route'})
        try:
            origin=urllib.parse.urlsplit(self.headers.get('Origin',''))
            if origin.netloc and origin.netloc!=self.headers.get('Host'):raise ValueError('Open this Theater page directly')
            with _RATE_LOCK:
                now=time.time();key=self.client_address[0]
                if len(_RATE)>1024:_RATE.clear()
                hits=[t for t in _RATE.get(key,[]) if now-t<60]
                _RATE[key]=hits+[now]
                if len(hits)>=10:return self.reply(429,{'error':'Wait a minute before trying another code'})
            size=int(self.headers.get('Content-Length','0'))
            if not 0<size<=256:raise ValueError('Invalid admission request')
            payload=json.loads(self.rfile.read(size))
            if not isinstance(payload,dict):raise ValueError('JSON object required')
            code=str(payload.get('code','')).upper().replace('-','').replace(' ','')
            ticket=theater.admission(code)
            age=max(0,int(ticket['expires']-time.time()))
            return self.reply(200,{'ok':True},cookie=f'{theater.COOKIE}={code}; HttpOnly; Secure; SameSite=Lax; Path=/; Max-Age={age}')
        except (ValueError,TypeError,KeyError):return self.reply(403,{'error':'Ticket expired, revoked, or unknown'})

    def do_HEAD(self):self.get(head=True)
    def do_GET(self):self.get()

    def get(self,head=False):
        path=urllib.parse.urlsplit(self.path).path
        if path=='/':return self.reply(200,PAGE,'text/html; charset=utf-8',head=head)
        if path not in {'/state','/stream'}:return self.reply(404,{'error':'Unknown Theater route'},head=head)
        try:
            value=theater.view(self.code())
            if path=='/state':return self.reply(200,value,head=head)
            if not value.get('media') or value.get('state')=='stopped':return self.reply(409,{'error':'No showing is running'},head=head)
            try:response=theater.media_request(value['media'],self.headers.get('Range'),head)
            except urllib.error.HTTPError as exc:response=exc
            with response:
                if response.status not in {200,206,416}:return self.reply(response.status,{'error':'The showing is unavailable. The host may still be preparing browser playback.'},head=head)
                self.send_response(response.status)
                for name in ('Content-Type','Content-Length','Content-Range','Accept-Ranges'):
                    if response.headers.get(name):self.send_header(name,response.headers[name])
                self.send_header('Cache-Control','private, no-store');self.send_header('X-Content-Type-Options','nosniff');self.end_headers()
                if head:return
                # Recheck admission while streaming so revocation stops an existing download.
                checked=0
                while True:
                    try:
                        if time.monotonic()-checked>=1:
                            current=theater.view(self.code())
                            if current.get('media')!=value['media'] or current.get('state')=='stopped':break
                            checked=time.monotonic()
                    except ValueError:break
                    block=response.read(65536)
                    if not block:break
                    try:self.wfile.write(block)
                    except (BrokenPipeError,ConnectionResetError):return
        except ValueError:return self.reply(403,{'error':'Enter a valid ticket to watch'},head=head)
        except (OSError,TimeoutError):return self.reply(503,{'error':'Media host unavailable'},head=head)


PAGE=r'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Fabric Theater</title><style>
:root{color-scheme:dark}*{box-sizing:border-box}body{margin:0;background:#10191d;color:#eee9dc;font:17px/1.5 system-ui}main{max-width:1200px;margin:auto;padding:28px}header{display:flex;justify-content:space-between;align-items:center;gap:16px}h1{font:normal 30px Georgia;color:#c6a66f}h2{font:normal 24px Georgia}video{width:100%;max-height:75vh;background:#080c0e;border-radius:8px}button,input{font:inherit;padding:12px;border:1px solid #627076;border-radius:6px;background:#1d2b31;color:inherit}button{cursor:pointer;color:#e4c890}form{display:flex;gap:10px;flex-wrap:wrap}p{color:#b4c0c3}#watch{font-weight:bold}button:focus-visible,input:focus-visible{outline:2px solid #83c9f4}footer{display:flex;gap:12px;margin-top:12px}@media(max-width:600px){main{padding:16px}h1{font-size:25px}}[hidden]{display:none!important}
</style><main><header><h1>Fabric Theater</h1><button id="full">Fullscreen</button></header><h2 id="title">Take your seat</h2><form id="admit"><input id="code" aria-label="Ticket code" placeholder="Ticket code" autocomplete="off" maxlength="20"><button>Enter</button></form><p id="status" role="status">Enter your ticket, or join an open showing.</p><video id="video" controls playsinline preload="metadata"></video><footer><button id="watch">Watch</button><button id="live" hidden>Join current position</button></footer></main><script>
const $=id=>document.getElementById(id),v=$('video');let state=null,media='',polling=false;
async function refresh(){if(polling)return;polling=true;try{const r=await fetch('/state');const d=await r.json();if(!r.ok){v.pause();v.removeAttribute('src');v.load();media='';$('admit').hidden=false;throw Error(d.error)}state=d;$('admit').hidden=true;$('title').textContent=d.title||'Between showings';$('live').hidden=d.mode!=='channel';$('status').textContent=d.mode==='channel'?(d.state==='playing'?'Now showing · shared playback':'Showing '+d.state):'Your ticket · watch at your own pace';if(d.media!==media){media=d.media||'';v.pause();if(media)v.src='/stream';else{v.removeAttribute('src');v.load()}}if(d.mode==='channel'&&media&&v.readyState){if(Math.abs(v.currentTime-d.position)>3)v.currentTime=d.position;if(d.state==='paused'||d.state==='stopped')v.pause();else if(v.dataset.started)v.play().catch(()=>{})}}catch(e){$('status').textContent=e.message}finally{polling=false}}
$('admit').onsubmit=async e=>{e.preventDefault();try{const r=await fetch('/admit',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({code:$('code').value})});const d=await r.json();if(!r.ok)throw Error(d.error);$('code').value='';await refresh()}catch(e){$('status').textContent=e.message}};
$('watch').onclick=async()=>{await refresh();if(!media)return;v.dataset.started='yes';if(state.mode==='channel')v.currentTime=state.position;v.play().catch(e=>$('status').textContent=e.message)};
$('live').onclick=()=>{if(state){v.currentTime=state.position;v.dataset.started='yes';if(state.state==='playing')v.play().catch(()=>{})}};
$('full').onclick=()=>{const target=v.requestFullscreen?v:v.parentElement;if(target.requestFullscreen)target.requestFullscreen();else if(v.webkitEnterFullscreen)v.webkitEnterFullscreen()};
v.onloadedmetadata=()=>{if(state?.mode==='channel')v.currentTime=state.position};v.onerror=()=>$('status').textContent='Playback unavailable. Ask the host to check this media file.';
const ticket=location.hash.slice(1);if(ticket){history.replaceState(null,'',location.pathname);$('code').value=ticket;$('admit').requestSubmit()}else refresh();setInterval(refresh,4000);
</script></html>'''
