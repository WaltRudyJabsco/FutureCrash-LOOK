"""Authenticated owner controls shared by Signal and Albert."""
import json
from pathlib import Path
import urllib.parse
import urllib.request
try:from .radio_web import send
except ImportError:from radio_web import send


def handle(handler,node_url,payload=None):
    parsed=urllib.parse.urlsplit(handler.path)
    if parsed.path=='/theater':return send(handler,200,PAGE,'text/html; charset=utf-8')
    if parsed.path=='/api/theater/config':
        try:owner=json.loads((Path.home()/'.config/look/media_storage.json').read_text()).get('node') or 'local'
        except (OSError,ValueError):owner='local'
        with urllib.request.urlopen(node_url+'/v1/nodes',timeout=5) as response:peers=json.load(response).get('peers',[])
        return send(handler,200,{'owner':owner,'owners':['local',*[p['name'] for p in peers if p.get('trusted')]]})
    if parsed.path!='/api/theater':raise ValueError('Unknown Theater route')
    query=urllib.parse.parse_qs(parsed.query)
    target=(query.get('target') or ['local'])[0]
    path='/v1/theater?'+urllib.parse.urlencode({'target':target})
    request=urllib.request.Request(node_url+path,data=json.dumps(payload or {'action':'status'}).encode(),headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(request,timeout=45) as response:return send(handler,200,json.load(response))


def post(handler,node_url):
    origin=urllib.parse.urlsplit(handler.headers.get('Origin',''))
    if origin.netloc and origin.netloc!=handler.headers.get('Host'):raise ValueError('Same-origin request required')
    size=int(handler.headers.get('Content-Length','0'))
    if not 0<size<=8192:raise ValueError('Invalid Theater request')
    value=json.loads(handler.rfile.read(size))
    if not isinstance(value,dict):raise ValueError('JSON object required')
    return handle(handler,node_url,value)


PAGE=r'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Fabric Theater · Projection room</title><style>
:root{color-scheme:dark}*{box-sizing:border-box}body{background:#10191d;color:#eee9dc;font:16px/1.5 system-ui;max-width:1000px;margin:auto;padding:24px}h1,h2{font-family:Georgia;font-weight:normal}h1{color:#c6a66f}a{color:#8ccbe6}input,button,select{font:inherit;padding:10px;background:#1d2b31;color:inherit;border:1px solid #52656e;border-radius:6px;min-height:44px}button{cursor:pointer;color:#e4c890}form,.tools{display:flex;gap:10px;flex-wrap:wrap;margin:14px 0}input{min-width:100px}input[type=search]{flex:1}section{padding:18px;background:#17252a;border-radius:10px;margin:20px 0}li{padding:12px 0;border-bottom:1px solid #34484d;list-style:none}ul{padding:0}p{color:#bac6c8}.selected{border-left:3px solid #c6a66f;padding-left:10px}#qr{background:white;width:220px;max-width:100%}button:focus-visible,input:focus-visible{outline:2px solid #83c9f4}#ticket-link{overflow-wrap:anywhere}
</style><h1>Fabric Theater</h1><a href="/">Back to chat</a><form id="host-form"><label>Media host <select id="host" aria-label="Media host"></select></label><button>Connect</button></form><p id="status" role="status">Connecting…</p><section><h2 id="now">Projection room</h2><p id="clock"></p><div class="tools"><button data-action="pause">Pause</button><button data-action="resume">Resume</button><button data-action="stop">End showing</button><button id="open">Open channel to visitors</button><button id="private">Require channel tickets</button></div><form id="seek"><label>Position in seconds <input id="seconds" type="number" min="0" max="86400" value="0"></label><button>Seek</button></form><a id="guest" target="_blank" rel="noopener">Open audience page ↗</a></section><section><h2>Choose a showing</h2><form id="search"><input id="query" type="search" placeholder="Search this host’s movies and music" aria-label="Search media"><button>Search</button></form><ul id="results"></ul></section><section><h2>Admission</h2><label>Ticket duration <select id="hours"><option value="24">One day</option><option value="120">Five days</option><option value="168">One week</option><option value="1">One hour</option></select></label><button id="channel-ticket">Issue channel ticket</button><div id="ticket" hidden><h3 id="ticket-title"></h3><a id="ticket-link" target="_blank" rel="noopener"></a><p id="ticket-code"></p><img id="qr" alt="Scan this Theater ticket"><p>Save or print the QR image to make a paper ticket.</p></div><ul id="tickets"></ul></section><details><summary>Set up this media host</summary><p>The audience service listens locally on port 7340. Point a dedicated HTTPS address at that port using Tailscale Serve or Funnel.</p><form id="setup"><input id="url" type="url" placeholder="https://HOST:8443" required aria-label="Theater HTTPS address"><button>Save Theater address</button></form></details><script>
const $=id=>document.getElementById(id);let target=new URLSearchParams(location.search).get('target')||localStorage.getItem('look-theater-owner')||'local';
async function api(value){const r=await fetch('/api/theater?'+new URLSearchParams({target}),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(value)});const d=await r.json();if(!r.ok||d.error)throw Error(d.error||'Theater host unavailable');return d}
function message(e){$('status').textContent=e.message||e}
async function refresh(){try{const d=await api({action:'status'});$('now').textContent=d.channel.title||'Between showings';$('clock').textContent=d.channel.state+' · '+Math.floor(d.channel.position||0)+' seconds';$('guest').href=d.settings.url||'#';$('guest').hidden=!d.settings.url;$('tickets').replaceChildren();for(const t of d.tickets){const li=document.createElement('li');li.textContent=(t.title||'Channel')+' · '+(t.revoked?'revoked':new Date(t.expires*1000).toLocaleString())+' ';if(!t.revoked&&t.expires>Date.now()/1000){const b=document.createElement('button');b.textContent='Revoke';b.onclick=()=>api({action:'revoke',id:t.id}).then(refresh).catch(message);li.append(b)}$('tickets').append(li)}message(d.settings.enabled?'Connected to '+target:'Set up an HTTPS Theater address below')}catch(e){message(e)}}
async function ticket(value){try{const d=await api({...value,action:'ticket',hours:Number($('hours').value)});$('ticket').hidden=false;$('ticket-title').textContent=d.title;$('ticket-link').href=d.url;$('ticket-link').textContent=d.url;$('ticket-code').textContent=d.code+' · expires '+new Date(d.expires*1000).toLocaleString();$('qr').hidden=true;try{const q=await api({action:'qr',code:d.code});$('qr').src='data:image/png;base64,'+q.png;$('qr').hidden=false}catch(e){message(e)}await refresh()}catch(e){message(e)}}
$('host-form').onsubmit=e=>{e.preventDefault();target=$('host').value;localStorage.setItem('look-theater-owner',target);refresh()};$('setup').onsubmit=async e=>{e.preventDefault();try{await api({action:'configure',url:$('url').value});refresh()}catch(e){message(e)}};
$('search').onsubmit=async e=>{e.preventDefault();try{const d=await api({action:'search',query:$('query').value});$('results').replaceChildren();for(const row of d.items){const li=document.createElement('li');li.textContent=row.title||row.id;const show=document.createElement('button');show.textContent='Show on channel';show.onclick=()=>api({action:'show',media:row.id}).then(refresh).catch(message);const t=document.createElement('button');t.textContent='Issue movie ticket';t.onclick=()=>ticket({media:row.id});li.append(document.createTextNode(' '),show,document.createTextNode(' '),t);$('results').append(li)}if(!d.items.length)message('No matching media on '+target)}catch(e){message(e)}};
for(const b of document.querySelectorAll('[data-action]'))b.onclick=()=>api({action:b.dataset.action}).then(refresh).catch(message);
$('seek').onsubmit=e=>{e.preventDefault();api({action:'seek',position:Number($('seconds').value)}).then(refresh).catch(message)};
$('open').onclick=()=>{if(confirm('Allow anyone with the Theater address to join the current channel?'))api({action:'access',public:true}).then(refresh).catch(message)};
$('private').onclick=()=>api({action:'access',public:false}).then(refresh).catch(message);$('channel-ticket').onclick=()=>ticket({scope:'channel'});async function init(){try{const r=await fetch('/api/theater/config');const d=await r.json();if(!localStorage.getItem('look-theater-owner')&&!location.search)target=d.owner;for(const owner of d.owners){const o=document.createElement('option');o.value=owner;o.textContent=owner;$('host').append(o)}$('host').value=target;refresh()}catch(e){message(e)}}init();
</script></html>'''
