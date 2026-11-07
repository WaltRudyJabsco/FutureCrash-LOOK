"""One authenticated animation channel for Signal and Albert."""
import json
from pathlib import Path
import urllib.parse
import urllib.request
try:from .radio_web import send
except ImportError:from radio_web import send

def handle(handler,node_url):
    parsed=urllib.parse.urlsplit(handler.path)
    if parsed.path=='/gypsy':return send(handler,200,PAGE,'text/html; charset=utf-8')
    try:owner=json.loads((Path.home()/'.config/look/animations.json').read_text()).get('node','local')
    except (ValueError,OSError):owner='local'
    params=urllib.parse.parse_qs(parsed.query)
    route={'/api/gypsy':'/v1/gypsy','/api/gypsy/image':'/v1/gypsy/image'}.get(parsed.path)
    if not route:raise ValueError('Unknown animation route')
    url=node_url+route+'?'+urllib.parse.urlencode({'target':owner,'id':(params.get('id') or [''])[0]})
    with urllib.request.urlopen(url,timeout=45) as response:
        handler.send_response(200)
        for key in ('Content-Type','Content-Length'):
            if response.headers.get(key):handler.send_header(key,response.headers[key])
        handler.send_header('Cache-Control','private, max-age=86400' if route.endswith('/image') else 'no-store');handler.end_headers()
        while block:=response.read(65536):handler.wfile.write(block)

PAGE=r'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Gypsy Astronaut · LOOK</title>
<style>:root{color-scheme:dark}*{box-sizing:border-box}body{margin:0;background:#080d13;color:#eee9df;font:16px system-ui}main{height:100dvh;display:flex;flex-direction:column}header,footer{padding:14px 22px;display:flex;align-items:center;gap:12px;flex-wrap:wrap}header{border-top:3px solid #b49b65}h1{font:24px Georgia;margin:0}#stage{flex:1;min-height:0;display:grid;place-items:center;overflow:hidden}img{width:100%;height:100%;object-fit:contain;min-height:0}button,select{background:#1d2935;color:#eee9df;border:1px solid #687887;border-radius:6px;padding:10px;font:inherit;cursor:pointer}a{color:#c6af79}#status{color:#aeb9c1;font-size:13px}footer{justify-content:center}#credit{max-width:60ch;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}main:fullscreen header{display:none}@media(max-width:600px){header,footer{padding:10px}h1{font-size:20px}}</style>
<main id="tv"><header><h1>Gypsy Astronaut</h1><span id="status">Loading the saved collection…</span></header><div id="stage"><img id="art" alt="Gypsy Astronaut animation" hidden></div><footer><button id="prev" aria-label="Previous animation">←</button><button id="hold">Hold</button><button id="next" aria-label="Next animation">→</button><label>Change every <select id="interval"><option value="10" selected>10s</option><option value="20">20s</option><option value="30">30s</option><option value="60">60s</option></select></label><button id="full">Fullscreen</button><a id="credit" target="_blank" rel="noopener" href="https://gypsyastronaut.tumblr.com/">Source & credits</a></footer></main>
<script>
const $=id=>document.getElementById(id);let rows=[],index=-1,held=false,timer;
function schedule(){clearTimeout(timer);if(!held&&rows.length)timer=setTimeout(()=>step(1),Number($('interval').value)*1000)}
function step(delta){if(!rows.length)return;index=(index+delta+rows.length)%rows.length;const row=rows[index];$('art').src='/api/gypsy/image?id='+encodeURIComponent(row.id);$('art').hidden=false;$('credit').textContent=row.title;$('credit').href=/^https:\/\/gypsyastronaut\.tumblr\.com\//.test(row.post)?row.post:'https://gypsyastronaut.tumblr.com/';schedule()}
$('art').onerror=()=>{$('status').textContent='Animation unavailable; trying the next saved item…';clearTimeout(timer);if(!held)timer=setTimeout(()=>step(1),3000)};
$('prev').onclick=()=>step(-1);$('next').onclick=()=>step(1);$('hold').onclick=()=>{held=!held;$('hold').textContent=held?'Resume slideshow':'Hold';schedule()};$('interval').onchange=schedule;
$('full').onclick=()=>{(document.fullscreenElement?document.exitFullscreen():$('tv').requestFullscreen()).catch(e=>$('status').textContent=e.message)};
document.addEventListener('keydown',e=>{if(['SELECT','INPUT','BUTTON'].includes(e.target.tagName))return;if(e.key==='ArrowRight')$('next').click();else if(e.key==='ArrowLeft')$('prev').click();else if(e.code==='Space'){e.preventDefault();$('hold').click()}else if(e.key.toLowerCase()==='f')$('full').click()});
async function refresh(){try{const response=await fetch('/api/gypsy');if(!response.ok)throw Error('Archive host unavailable');const data=await response.json();const incoming=Object.values(data.items||{}).filter(x=>x.sha256);const known=new Set(rows.map(x=>x.id));const added=incoming.filter(x=>!known.has(x.id));for(let i=added.length-1;i>0;i--){const j=Math.floor(Math.random()*(i+1));[added[i],added[j]]=[added[j],added[i]]}rows.push(...added);$('status').textContent=rows.length+' saved animations · '+data.state+(data.error?' · '+data.error:'');if(index<0&&rows.length)step(1);if(!rows.length)$('status').textContent+=' · Run lk gypsy sync on your archive host.'}catch(e){$('status').textContent=e.message}setTimeout(refresh,15000)}refresh();
</script></html>'''
