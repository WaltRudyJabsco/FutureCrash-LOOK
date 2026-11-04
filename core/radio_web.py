"""Same-origin YTR browser edge; queue authority remains on the chosen Fabric node."""
import json
from pathlib import Path
import urllib.parse
import urllib.request
import urllib.error


def send(handler, status, body, content='application/json'):
    data=body.encode() if isinstance(body,str) else json.dumps(body).encode()
    handler.send_response(status)
    handler.send_header('Content-Type',content)
    handler.send_header('Content-Length',str(len(data)))
    handler.send_header('Cache-Control','private, no-store')
    handler.send_header('X-Content-Type-Options','nosniff')
    handler.end_headers();handler.wfile.write(data)


def handle(handler,node_url,payload=None):
    """Both hosts require lo.use before entering this allowlisted gateway."""
    parsed=urllib.parse.urlsplit(handler.path)
    if parsed.path=='/ytr':return send(handler,200,PAGE,'text/html; charset=utf-8')
    if parsed.path=='/api/ytr/config':
        if payload is not None:raise ValueError('Configuration is read-only')
        try:owner=json.loads((Path.home()/'.config/look/radio.json').read_text()).get('node') or 'local'
        except (OSError,ValueError):owner='local'
        peers=[]
        try:
            with urllib.request.urlopen(node_url+'/v1/nodes',timeout=5) as response:
                peers=json.load(response).get('peers',[])
        except (OSError,ValueError):pass
        return send(handler,200,{'owner':owner,'owners':['local',*[p['node'] for p in peers if p.get('trusted') and isinstance(p.get('node'),str)]]})
    route={'/api/ytr':'/v1/radio','/api/ytr/audio':'/v1/radio/audio'}.get(parsed.path)
    if route is None:raise ValueError('Unknown radio route')
    if payload is not None:
        if parsed.path!='/api/ytr' or payload.get('action') not in {'add','move','remove','retry','progress'}:
            raise ValueError('Unknown radio action')
    params=urllib.parse.parse_qs(parsed.query)
    query={k:v[0] for k,v in params.items() if k in {'target','id'}}
    headers={'Content-Type':'application/json'}
    if handler.headers.get('Range'):headers['Range']=handler.headers['Range']
    request=urllib.request.Request(node_url+route+'?'+urllib.parse.urlencode(query),
        data=json.dumps(payload).encode() if payload is not None else None,headers=headers)
    try:
        response=urllib.request.urlopen(request,timeout=30)
    except urllib.error.HTTPError as exc:response=exc
    with response:
        handler.send_response(response.status)
        for key in ('Content-Type','Content-Length','Content-Range','Accept-Ranges'):
            if response.headers.get(key):handler.send_header(key,response.headers[key])
        handler.send_header('Cache-Control','private, no-store')
        handler.send_header('X-Content-Type-Options','nosniff');handler.end_headers()
        while block:=response.read(65536):handler.wfile.write(block)


def post(handler,node_url):
    if handler.headers.get('Content-Type','').split(';')[0]!='application/json':raise ValueError('JSON required')
    origin=handler.headers.get('Origin')
    if origin and urllib.parse.urlsplit(origin).netloc!=handler.headers.get('Host'):raise ValueError('Same-origin request required')
    size=int(handler.headers.get('Content-Length') or 0)
    if not 0<size<=8192:raise ValueError('Invalid radio request size')
    payload=json.loads(handler.rfile.read(size))
    if not isinstance(payload,dict):raise ValueError('Invalid radio request')
    return handle(handler,node_url,payload)


PAGE=r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>YouTube Radio · LOOK</title><style>
:root{color-scheme:dark;--bg:#101923;--panel:#172430;--ink:#e0e9ed;--muted:#9bb0bd;--blue:#83c9f4;--line:#344958}
*{box-sizing:border-box}body{margin:0 auto;padding:24px;max-width:860px;background:var(--bg);color:var(--ink);font:16px/1.5 system-ui}h1{font-size:25px;margin:0}small,.hint{color:var(--muted)}header,.tools,form{display:flex;gap:10px;align-items:center;flex-wrap:wrap}header{justify-content:space-between}a{color:var(--blue)}button,input,select{font:inherit;color:var(--ink);background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:10px;min-height:44px}button{cursor:pointer}button:disabled{opacity:.45;cursor:default}button:focus-visible,input:focus-visible,select:focus-visible{outline:2px solid var(--blue);outline-offset:3px}button.primary{color:var(--bg);background:var(--blue);font-weight:650}form{margin:16px 0}input{flex:1;min-width:130px}.deck{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:18px;margin-top:18px}.deck h2{font-size:19px;margin:8px 0;overflow-wrap:anywhere}audio{width:100%;margin:10px 0}#reels{display:block;width:100%;height:96px;color:var(--blue)}.spokes{transform-box:fill-box;transform-origin:center;animation:spin 7s linear infinite;animation-play-state:paused}.playing .spokes{animation-play-state:running}@keyframes spin{to{transform:rotate(360deg)}}@media(prefers-reduced-motion:reduce){.spokes{animation:none}}#queue{list-style:none;padding:0}#queue li{padding:14px 0;border-bottom:1px solid var(--line)}#queue li.active{border-left:3px solid var(--blue);padding-left:12px}.title{font-weight:600;overflow-wrap:anywhere}.rowinfo{font-size:13px;color:var(--muted);margin:5px 0}.tools button{font-size:14px;padding:6px 10px}#status{min-height:24px;color:var(--muted)}#conflict{border:1px solid #d8ad74;padding:12px;border-radius:8px}#position{font-variant-numeric:tabular-nums}#play{min-width:120px}select{max-width:100%}@media(max-width:480px){body{padding:14px}.deck{padding:12px}header{align-items:flex-start}.tools{gap:6px}}
</style></head><body>
<header><div><small>LOOK · LISTEN LATER</small><h1>YouTube Radio</h1></div><a href="/">Back to chat</a></header>
<form id="owner-form"><label for="owner">Queue owner</label><select id="owner" aria-label="Queue owner"></select><button>Use queue</button></form>
<p class="hint">The same queue and listening positions as lk ytr. Audio plays on this device.</p>
<form id="add-form"><input id="url" type="url" required placeholder="Paste a YouTube video link" aria-label="YouTube video link"><button class="primary">Add to queue</button></form>
<div id="status" role="status" aria-live="polite">Connecting…</div>
<div id="conflict" hidden><p id="conflict-text">A listening position needs review.</p><button id="remote">Use saved position</button> <button id="local">Keep this device’s position</button></div>
<section class="deck" aria-label="Audio player">
<svg id="reels" viewBox="0 0 600 110" role="img" aria-label="Two tape reels"><g fill="none" stroke="currentColor" stroke-width="2"><path d="M40 92 Q80 78 120 92 T200 92 T280 92 T360 92 T440 92 T560 92" opacity=".35"/>
<circle cx="190" cy="48" r="36" fill="#172430"/><circle cx="410" cy="48" r="36" fill="#172430"/>
<g class="spokes"><circle cx="190" cy="48" r="29" stroke-opacity=".3"/><path d="M190 20 V76 M166 34 L214 62 M166 62 L214 34"/></g>
<g class="spokes"><circle cx="410" cy="48" r="29" stroke-opacity=".3"/><path d="M410 20 V76 M386 34 L434 62 M386 62 L434 34"/></g><circle cx="190" cy="48" r="5" fill="#172430"/><circle cx="410" cy="48" r="5" fill="#172430"/></g></svg>
<h2 id="now">Choose something from your queue</h2><div id="position">0:00 / —</div>
<audio id="audio" controls preload="metadata"></audio>
<div class="tools"><button id="play" class="primary" disabled>Play</button><button id="next" disabled>Next</button><label>Speed <select id="speed"><option>0.75</option><option selected>1</option><option>1.25</option><option>1.5</option><option>2</option></select></label></div>
</section><h2>Listen-later queue</h2><ol id="queue"></ol>
<script src="/browser-views.js"></script>
<script>
'use strict';
const $=id=>document.getElementById(id),audio=$('audio');
let owner='',items=[],current=null,saving=null,loading=false,polling=false,conflicted=false,signature='',lastSave=0;
const memory=new Map();
const storage={get(k){try{return JSON.parse(localStorage.getItem(k))??memory.get(k)??null}catch{return memory.get(k)??null}},set(k,v){memory.set(k,v);try{localStorage.setItem(k,JSON.stringify(v))}catch{}},remove(k){memory.delete(k);try{localStorage.removeItem(k)}catch{}}};
const key=id=>'look-ytr-bookmark:'+owner+':'+id;
const time=n=>{n=Math.max(0,Math.floor(Number(n)||0));return n>=3600?Math.floor(n/3600)+':'+String(Math.floor(n/60)%60).padStart(2,'0')+':'+String(n%60).padStart(2,'0'):Math.floor(n/60)+':'+String(n%60).padStart(2,'0')};
const stamp=(p,d)=>time(p)+' / '+(d?time(d):'—');
function status(s){$('status').textContent=s}
function route(suffix=''){return '/api/ytr'+suffix+'?'+new URLSearchParams({target:owner})}
async function api(payload){const response=await fetch(route(),{method:payload?'POST':'GET',headers:payload?{'Content-Type':'application/json'}:{},body:payload?JSON.stringify(payload):undefined,signal:AbortSignal.timeout(30000)});const data=await response.json();if(!response.ok||!data.ok)throw Error(data.error||'Queue unavailable');return data}
function remember(done=false){if(!current||loading||conflicted)return;const position=audio.currentTime||0,finished=done||audio.ended;if(Math.abs(position-(current.position||0))<.05&&finished===!!current.done)return;storage.set(key(current.id),{id:current.id,position,done:finished,bookmark_revision:current.bookmark_revision})}
async function save(done=false){
 if(!current||loading)return true;
 if(conflicted)return false;
 if(saving){await saving;return save(done)}
 remember(done);const id=current.id,pending=storage.get(key(id));if(!pending)return true;
 saving=(async()=>{try{const state=await api({...pending,action:'progress'});const row=state.items.find(x=>x.id===id);if(current?.id===id){current.bookmark_revision=row.bookmark_revision;current.position=row.position;current.done=row.done}
 const latest=storage.get(key(id));if(latest&&latest.position===pending.position&&latest.done===pending.done)storage.remove(key(id));else if(latest){latest.bookmark_revision=row.bookmark_revision;storage.set(key(id),latest)}
 items=state.items;return true;
 }catch(e){audio.pause();conflicted=true;$('conflict').hidden=false;$('conflict-text').textContent=e.message+' Your position is retained on this browser.';status('Listening position not synchronized');return false}finally{saving=null}})();return saving;
}
function draw(){
 const value=JSON.stringify([items,current?.id]);if(value===signature)return;signature=value;
 $('queue').replaceChildren();if(!items.length){$('queue').textContent='Your queue is empty. Add a YouTube link above.';return}
 items.forEach((item,index)=>{const li=document.createElement('li');if(item.id===current?.id)li.className='active';const title=document.createElement('div');title.className='title';title.textContent=(index+1)+'. '+(item.title||item.url);li.append(title);
 const info=document.createElement('div');info.className='rowinfo';info.dataset.id=item.id;info.textContent=stamp(item.position,item.duration)+' · '+(item.done?'Finished':item.stage)+(item.error?' · '+item.error:'');li.append(info);
 const controls=document.createElement('div');controls.className='tools';
 function button(label,fn,disabled=false){const b=document.createElement('button');b.textContent=label;b.disabled=disabled;b.onclick=()=>Promise.resolve(fn()).catch(e=>status(e.message));controls.append(b)}
 button(item.id===current?.id?'Resume':'Play',()=>start(item),item.stage!=='complete');button('↑',()=>mutate({action:'move',id:item.id,delta:-1}),index===0);button('↓',()=>mutate({action:'move',id:item.id,delta:1}),index===items.length-1);
 if(['failed','cancelled','expired'].includes(item.stage))button('Retry',()=>mutate({action:'retry',id:item.id}));
 button('Remove',async()=>{if(item.id===current?.id){audio.pause();if(!await save())return;audio.removeAttribute('src');audio.load();current=null;$('now').textContent='Choose something from your queue';$('play').disabled=true;$('next').disabled=true}await mutate({action:'remove',id:item.id});storage.remove(key(item.id))});
 const link=document.createElement('a');link.textContent='Original ↗';link.href=item.url;link.target='_blank';link.rel='noopener';controls.append(link);li.append(controls);$('queue').append(li)});
}
async function mutate(payload){items=(await api(payload)).items;draw();status('Queue updated')}
async function start(item){
 if(loading)return;
 if(current?.id===item.id){if(!conflicted)await audio.play();return}
 if(current){audio.pause();if(!await save())return}
 const pending=storage.get(key(item.id));current={...item};conflicted=false;$('conflict').hidden=true;
 if(pending){conflicted=true;$('conflict').hidden=false;$('conflict-text').textContent='This browser has an unsynchronized position. Choose which position to keep.';status('Review saved position before playing');return}
 loadCurrent(item.done?0:item.position);
}
function loadCurrent(position){loading=true;$('now').textContent=current.title||current.url;$('play').disabled=false;$('next').disabled=false;audio.src=route('/audio')+'&'+new URLSearchParams({id:current.id});
 audio.onloadedmetadata=()=>{audio.currentTime=Math.min(position||0,Number.isFinite(audio.duration)?Math.max(0,audio.duration-.1):position||0);loading=false;updateTime()};
 audio.playbackRate=Number($('speed').value);audio.play().catch(()=>status('Ready—press Play to listen'));draw();
}
function updateTime(){if(!current)return;const total=Number.isFinite(audio.duration)?audio.duration:current.duration;$('position').textContent=stamp(audio.currentTime,total)+(total?' · '+time(Math.max(0,total-audio.currentTime))+' left':'');const row=document.querySelector('[data-id="'+current.id+'"]');if(row)row.textContent=stamp(audio.currentTime,total)+' · Listening';}
audio.ontimeupdate=()=>{updateTime();remember();if(Date.now()-lastSave>5000){lastSave=Date.now();save()}};
audio.onplay=()=>{if(conflicted){audio.pause();return status('Resolve the saved position first')}document.body.classList.add('playing');$('play').textContent='Pause'};
audio.onpause=()=>{document.body.classList.remove('playing');$('play').textContent='Play';remember();if(!loading&&!conflicted)save()};
audio.onerror=()=>{loading=false;status('Audio unavailable. Reconnect to the queue owner or retry the item.')};
audio.onended=async()=>{if(await save(true))await next()};
async function next(){const index=items.findIndex(x=>x.id===current?.id);const item=items[index+1];if(item?.stage==='complete')await start(item);else status(item?'Next item is still preparing':'End of queue')}
$('next').onclick=()=>next().catch(e=>status(e.message));
$('play').onclick=()=>{if(conflicted)return status('Resolve the saved position first');if(audio.paused)audio.play().catch(e=>status(e.message));else{audio.pause();save()}};
$('speed').onchange=()=>{audio.playbackRate=Number($('speed').value)};
$('remote').onclick=async()=>{try{const state=await api();const row=state.items.find(x=>x.id===current?.id);if(!row)throw Error('Item no longer in queue');storage.remove(key(row.id));current=row;conflicted=false;$('conflict').hidden=true;loadCurrent(row.done?0:row.position)}catch(e){status(e.message)}};
$('local').onclick=async()=>{try{const state=await api();const row=state.items.find(x=>x.id===current?.id),pending=current&&storage.get(key(current.id));if(!row||!pending)throw Error('No pending position');const result=await api({...pending,bookmark_revision:row.bookmark_revision,action:'progress'});current=result.items.find(x=>x.id===row.id);storage.remove(key(row.id));conflicted=false;$('conflict').hidden=true;loadCurrent(current.done?0:current.position)}catch(e){status(e.message)}};
$('add-form').onsubmit=async e=>{e.preventDefault();try{await mutate({action:'add',url:$('url').value.trim()});$('url').value=''}catch(error){status(error.message)}};
$('owner-form').onsubmit=async e=>{e.preventDefault();if(loading)return;if(current){audio.pause();if(!await save())return}owner=$('owner').value;storage.set('look-ytr-owner',owner);current=null;audio.removeAttribute('src');audio.load();$('now').textContent='Choose something from your queue';$('play').disabled=true;$('next').disabled=true;signature='';items=[];draw();await refresh()};
async function refresh(){if(polling||!owner)return;polling=true;const requested=owner;try{const state=await api();if(owner===requested){items=state.items;draw();if(!conflicted)status('Queue owner · '+state.node)}}catch(e){status(e.message+' · Reconnecting; pending positions stay in this browser.')}finally{polling=false}}
window.addEventListener('pagehide',()=>remember());document.addEventListener('visibilitychange',()=>{if(document.hidden)save()});
(async()=>{try{const config=await (await fetch('/api/ytr/config')).json();owner=storage.get('look-ytr-owner')||config.owner||'local';for(const name of new Set([owner,...config.owners])){const option=document.createElement('option');option.value=name;option.textContent=name;$('owner').append(option)}$('owner').value=owner;const link=new URLSearchParams(location.search).get('url');if(link)$('url').value=link;await refresh()}catch(e){status(e.message)}setInterval(refresh,5000)})();
</script></body></html>'''
