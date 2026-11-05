"""Authenticated museum gallery shared by Signal and Albert."""
import json
from pathlib import Path
import urllib.parse
import urllib.request
import urllib.error
try:from .radio_web import send
except ImportError:from radio_web import send


def handle(handler,node_url,payload=None):
    parsed=urllib.parse.urlsplit(handler.path)
    if parsed.path=='/museum':return send(handler,200,PAGE,'text/html; charset=utf-8')
    if parsed.path=='/api/museum/config':
        if payload is not None:raise ValueError('Configuration is read-only')
        try:owner=json.loads((Path.home()/'.config/look/museum.json').read_text()).get('node') or 'local'
        except (OSError,ValueError):owner='local'
        peers=[]
        try:
            with urllib.request.urlopen(node_url+'/v1/nodes',timeout=5) as response:peers=json.load(response).get('peers',[])
        except (OSError,ValueError):pass
        return send(handler,200,{'owner':owner,'owners':['local',*[p['name'] for p in peers if p.get('trusted') and isinstance(p.get('name'),str)]]})
    route={'/api/museum':'/v1/museum','/api/museum/search':'/v1/museum/search','/api/museum/image':'/v1/museum/image'}.get(parsed.path)
    if not route:raise ValueError('Unknown museum route')
    if payload is not None and (parsed.path!='/api/museum' or payload.get('action') not in {'save','pin','sync','favorite','starter','featured','cancel','collection-create','collection-add','collection-remove'}):raise ValueError('Unknown museum action')
    query={k:v[0] for k,v in urllib.parse.parse_qs(parsed.query).items() if k in {'target','id','source','q','page'}}
    request=urllib.request.Request(node_url+route+'?'+urllib.parse.urlencode(query),data=json.dumps(payload).encode() if payload is not None else None,headers={'Content-Type':'application/json'})
    try:response=urllib.request.urlopen(request,timeout=90)
    except urllib.error.HTTPError as exc:response=exc
    with response:
        handler.send_response(response.status)
        for name in ('Content-Type','Content-Length'):
            if response.headers.get(name):handler.send_header(name,response.headers[name])
        handler.send_header('Cache-Control','private, no-store');handler.send_header('X-Content-Type-Options','nosniff');handler.end_headers()
        while block:=response.read(65536):handler.wfile.write(block)


def post(handler,node_url):
    if handler.headers.get('Content-Type','').split(';')[0]!='application/json':raise ValueError('JSON required')
    origin=handler.headers.get('Origin')
    if origin and urllib.parse.urlsplit(origin).netloc!=handler.headers.get('Host'):raise ValueError('Same-origin request required')
    size=int(handler.headers.get('Content-Length') or 0)
    if not 0<size<=8192:raise ValueError('Invalid museum request size')
    data=json.loads(handler.rfile.read(size))
    if not isinstance(data,dict):raise ValueError('Invalid museum request')
    return handle(handler,node_url,data)


PAGE=r'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>LOOK Museum</title><style>
:root{color-scheme:light;--paper:#f5f0e6;--ink:#24374a;--muted:#626c72;--line:#d4ccba;--accent:#315c80;--panel:#fffdf7}*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:16px/1.5 system-ui}header,main{max-width:1200px;margin:auto;padding:24px}header{display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid var(--line)}h1{font:38px Georgia,serif;margin:0}h2{font:25px Georgia,serif;margin:12px 0}small,.muted{color:var(--muted)}a{color:var(--accent)}nav,form,.actions{display:flex;align-items:center;flex-wrap:wrap;gap:8px}button,input,select{font:inherit;padding:9px 13px;min-height:44px;border-radius:6px;border:1px solid var(--line);background:var(--panel);color:var(--ink)}button{cursor:pointer}button:disabled{opacity:.5;cursor:default}button.active,button.primary{background:var(--accent);color:white}button:focus-visible,input:focus-visible,select:focus-visible{outline:3px solid #b29151;outline-offset:3px}input[type=search]{flex:1;min-width:150px}#count{width:95px}form{margin:15px 0}#status{min-height:26px;color:var(--muted)}#grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:22px;margin:24px 0}.card{background:var(--panel);border:1px solid var(--line);padding:12px;display:flex;flex-direction:column}.card img{width:100%;height:230px;object-fit:contain;background:#ece7dc}.card .view{border:0;padding:0;background:transparent}.card h2{font-size:20px}.card p{margin:4px 0;font-size:14px}.card .actions{margin-top:auto;padding-top:12px}.card button{font-size:14px}dialog{max-width:min(1000px,96vw);max-height:95dvh;background:var(--paper);color:var(--ink);border:1px solid var(--line);padding:20px}dialog::backdrop{background:#101722df}#large{display:block;max-width:100%;height:55vh;object-fit:contain;margin:auto}#detail-text{max-width:75ch}#show{position:fixed;inset:0;z-index:20;background:#0c1116;color:#f5f0e6;padding:20px;display:flex;flex-direction:column;align-items:center}#show[hidden]{display:none}#show img{flex:1;min-height:0;max-height:calc(100dvh - 150px);width:100%;object-fit:contain}#show p{margin:10px;max-width:90%;text-align:center}#show .actions{flex:none}#job{padding:12px;border-left:3px solid #b29151;margin:16px 0}#job[hidden]{display:none}@media(max-width:500px){header,main{padding:14px}h1{font-size:30px}#grid{grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}.card{padding:8px}.card img{height:150px}.card h2{font-size:17px}.card .actions{gap:4px}.card button{padding:7px;font-size:12px}dialog{padding:12px}#large{height:42vh}}
</style></head><body><header><div><small>LOOK · AN OPEN COLLECTION</small><h1>Museum</h1></div><a href="/">Back to chat</a></header><main>
<nav><button id="saved" class="active">Library</button><button id="discover">Discover</button><button id="collections">Collections</button><button id="favorites">Favorites</button><button id="slideshow">Slideshow</button></nav>
<form id="owner-form"><label for="owner">Library owner / downloads go to</label><select id="owner"></select><button>Use library</button><button type="button" id="sync">Keep this view on this host</button></form>
<div class="actions"><select id="collection-choice" aria-label="Named collection" hidden></select><button id="new-collection">New collection</button><button id="featured">Download museum highlights</button><label><input id="offline-only" type="checkbox"> Available offline on this host</label><label><input id="shuffle" type="checkbox"> Shuffle slideshow</label></div><form id="search"><input id="query" type="search" placeholder="Artist, subject, period…" aria-label="Search art"><select id="source" aria-label="Museum source" hidden><option value="met">The Met</option><option value="aic">Art Institute of Chicago</option></select><button class="primary">Search</button></form>
<details><summary>Build starter library</summary><p>Chosen themes across painting, prints, sculpture, photography and decorative arts. Downloads only works marked public domain by the museum. Up to 20 MB per image; 3 GiB collection budget. Saved items are reused.</p><label>Works <input id="count" type="number" min="1" max="1000" value="1000"></label> <button id="starter">Build on selected owner</button></details>
<div id="job" hidden></div><p id="status" role="status" aria-live="polite">Opening the collection…</p><div id="grid"></div><div class="actions"><button id="previous" hidden>Previous page</button><button id="next" hidden>Next page</button></div>
</main><dialog id="detail"><button id="close">Close</button><img id="large" alt=""><h2 id="title"></h2><p id="credit"></p><p id="detail-text"></p><a id="origin" target="_blank" rel="noopener">View museum record ↗</a></dialog>
<div id="show" hidden><img id="slide-image" alt=""><p id="slide-caption"></p><div class="actions"><button id="slide-prev">Previous</button><button id="slide-pause">Pause</button><button id="slide-next">Next</button><button id="full">Fullscreen</button><button id="exit">Exit slideshow</button></div></div>
<script src="/browser-views.js"></script><script>
'use strict';const $=id=>document.getElementById(id);let owner='local',mode='saved',items=[],page=1,more=false,busy=false,slides=[],slide=0,timer=null,requestNumber=0,collections={},collectionId="",offline=false;
function status(value){$('status').textContent=value}
function endpoint(suffix='',extra={}){return '/api/museum'+suffix+'?'+new URLSearchParams({target:owner,...extra})}
async function api(suffix='',payload=null,extra={}){const response=await fetch(endpoint(suffix,extra),{method:payload?'POST':'GET',headers:payload?{'Content-Type':'application/json'}:{},body:payload?JSON.stringify(payload):undefined,signal:AbortSignal.timeout(100000)});const data=await response.json();if(!response.ok||!data.ok)throw Error(data.error||'Museum unavailable');return data}
function imageURL(row){if(offline&&!row.available_offline)return '';return row.downloaded||row.available_offline?endpoint('/image',{id:row.id}):row.image_url}
function safeImage(row){if(!imageURL(row))return '';try{const url=new URL(imageURL(row),location.href);if(url.origin===location.origin||url.protocol==='https:'&&['images.metmuseum.org','www.artic.edu'].includes(url.hostname))return url.href}catch{}return ''}
function open(row){$('large').src=safeImage(row);$('large').alt=row.title;$('title').textContent=row.title;$('credit').textContent=[row.artist,row.date,row.medium,row.museum,'CC0'].filter(Boolean).join(' · ');$('detail-text').textContent=row.description;$('origin').href=row.source==='met'?'https://www.metmuseum.org/art/collection/search/'+row.id.split('-')[1]:'https://www.artic.edu/artworks/'+row.id.split('-')[1];$('detail').showModal()}
function visible(){return items.filter(x=>(mode!=='favorites'||x.favorite)&&(mode!=='collections'||(x.collections||[]).includes(collectionId))&&(!$('offline-only').checked||x.available_offline))}
function collectionChoices(){const select=$('collection-choice');select.replaceChildren();for(const [id,value] of Object.entries(collections)){const option=document.createElement('option');option.value=id;option.textContent=value.name;select.append(option)}if(!collections[collectionId])collectionId=Object.keys(collections)[0]||'';select.value=collectionId;select.hidden=mode!=='collections'}
function draw(){
 $('grid').replaceChildren();const rows=visible();
 if(!rows.length){$('grid').textContent=mode==='discover'?'No open-access images found. Try another subject or museum.':mode==='collections'?'This collection is empty. Save works to Library, then add them to a collection.':'No matching works. Try Library, Discover, or turn off the offline filter.'}
 rows.forEach(row=>{const card=document.createElement('article');card.className='card';const view=document.createElement('button');view.className='view';view.setAttribute('aria-label','View '+row.title);const image=document.createElement('img');image.loading='lazy';image.src=safeImage(row);image.hidden=!safeImage(row);view.disabled=!safeImage(row);image.alt=row.title;view.append(image);view.onclick=()=>open(row);card.append(view);const title=document.createElement('h2');title.textContent=row.title;card.append(title);
 for(const value of [[row.artist,row.date].filter(Boolean).join(' · '),row.museum,offline?(row.available_offline?'Cached image available on this host':'Original unavailable offline'):(row.available_offline?'Available on this host; owner '+owner:row.downloaded?'Saved on '+owner:'Online · not saved')]){const p=document.createElement('p');p.textContent=value;card.append(p)}
 const controls=document.createElement('div');controls.className='actions';function button(label,action){const b=document.createElement('button');b.textContent=label;b.onclick=async()=>{b.disabled=true;try{await action()}catch(e){status(e.message)}finally{b.disabled=false}};controls.append(b)}
 if(!offline&&!row.downloaded)button('Save to '+owner,async()=>{await api('',{action:'save',id:row.id});row.downloaded=true;status('Downloaded on '+owner);draw()});
 if(row.downloaded&&!offline){button(row.favorite?'★ Favorite':'☆ Favorite',async()=>{await api('',{action:'favorite',id:row.id});row.favorite=!row.favorite;draw()});if(owner!=='local')button('Keep on this host',async()=>{await api('',{action:'pin',id:row.id});status('Copied to this browser host for offline use—not to the phone/browser storage.')})}
 if(row.downloaded&&!offline&&Object.keys(collections).length){button(mode==='collections'?'Remove from collection':'Add to collection',async()=>{
 let id=collectionId;if(mode!=='collections'){const keys=Object.keys(collections);const choice=prompt(keys.map((key,n)=>(n+1)+': '+collections[key].name).join('\n')+'\nChoose collection number');if(choice===null)return;id=keys[Number(choice)-1];if(!id)return}
 await api('',{action:mode==='collections'?'collection-remove':'collection-add',id:row.id,collection:id});await load()
 })}
 card.append(controls);$('grid').append(card)});
 $('previous').hidden=mode!=='discover'||page<=1;$('next').hidden=mode!=='discover'||!more;
}
function job(data){const value=data.job||{};$('job').hidden=!value.state;$('job').replaceChildren();if(!value.state)return;const p=document.createElement('p');p.textContent='Download · '+value.state+' · '+value.saved+'/'+value.requested+' · '+(value.theme||'')+(value.counts?' · '+Object.entries(value.counts).map(([name,count])=>name+': '+count).join(' · '):'');$('job').append(p);if(value.errors?.length){const note=document.createElement('p');note.textContent='Latest source issue: '+value.errors.at(-1);$('job').append(note)}if(value.state==='running'){const b=document.createElement('button');b.textContent='Stop download';b.onclick=()=>api('',{action:'cancel'}).then(data=>{job(data);status('Download stop requested')}).catch(e=>status(e.message));$('job').append(b)}}
async function load(){const serial=++requestNumber;busy=true;status(mode==='discover'?'Searching museum records…':'Loading saved collection…');try{const data=await api(mode==='discover'?'/search':'',null,mode==='discover'?{q:$('query').value,source:$('source').value,page}:{q:$('query').value});if(serial!==requestNumber)return;items=data.items;more=data.more;offline=!!data.offline;collections=data.collections||collections;collectionChoices();job(data);draw();$('new-collection').disabled=offline;$('starter').disabled=offline;$('featured').disabled=offline;status(items.length+' works · '+(offline?'Owner offline; cached catalog · '+data.offline_count+' images on this host':mode==='discover'?'Online museum search':'Library on '+owner))}catch(e){if(serial===requestNumber){if(mode==='discover'){items=[];draw()}status(e.message)}}finally{if(serial===requestNumber)busy=false}}
function switchMode(value){mode=value;page=1;$('source').hidden=value!=='discover';$('collection-choice').hidden=value!=='collections';for(const id of ['saved','discover','collections','favorites'])$(id).classList.toggle('active',id===value);if(value==='discover'&&!$('query').value)$('query').value='landscape';load()}
$('saved').onclick=()=>switchMode('saved');$('collections').onclick=()=>switchMode('collections');$('collection-choice').onchange=()=>{collectionId=$('collection-choice').value;draw()};$('offline-only').onchange=draw;$('new-collection').onclick=async()=>{const name=prompt('New collection name on '+owner);if(!name)return;try{const data=await api('',{action:'collection-create',name});collectionId=data.active_collection;switchMode('collections')}catch(e){status(e.message)}};$('discover').onclick=()=>switchMode('discover');$('favorites').onclick=()=>switchMode('favorites');$('search').onsubmit=e=>{e.preventDefault();page=1;load()};$('previous').onclick=()=>{page--;load()};$('next').onclick=()=>{page++;load()};$('close').onclick=()=>$('detail').close();
$('owner-form').onsubmit=e=>{e.preventDefault();exit();owner=$('owner').value;try{localStorage.setItem('look-museum-owner',owner)}catch{}page=1;items=[];collections={};collectionId='';offline=false;collectionChoices();draw();load()};
$('sync').onclick=async()=>{if(owner==='local')return status('These works are already on the browser host.');const ids=visible().filter(x=>x.downloaded).map(x=>x.id);if(!ids.length)return status('No saved works in this view to copy.');if(!confirm('Keep '+ids.length+' works from this view on the computer hosting this page? Source: '+owner+'. This does not download to your phone/tablet.'))return;try{const result=await api('',{action:'sync',ids});job(result);status('Copying this view to the browser host. Library owner remains '+owner+'.')}catch(e){status(e.message)}};
$('featured').onclick=async()=>{if(!confirm('Download up to 500 Met Highlights and 500 Art Institute Featured works on '+owner+'? These are museum selections, not visitor popularity rankings. Existing images are reused; 3 GiB total budget.'))return;try{job(await api('',{action:'featured',count:500,source:'both'}));status('Museum selections downloading on '+owner)}catch(e){status(e.message)}};
$('starter').onclick=async()=>{const count=Number($('count').value);if(!Number.isInteger(count)||count<1||count>1000)return status('Choose 1–1000 works');if(!confirm('Download up to '+count+' open-access artworks on '+owner+'? The collection has a 3 GiB budget; existing works are reused.'))return;try{job(await api('',{action:'starter',count}));status('Starter download running on '+owner)}catch(e){status(e.message)}};
function showSlide(){if(!slides.length)return;slide=(slide+slides.length)%slides.length;const row=slides[slide];$('slide-image').src=safeImage(row);$('slide-image').alt=row.title;$('slide-caption').textContent=[row.title,row.artist,row.date,row.museum].filter(Boolean).join(' · ')}
function shuffleWorks(rows,last=''){const result=[...rows];for(let i=result.length-1;i>0;i--){const j=Math.floor(Math.random()*(i+1));[result[i],result[j]]=[result[j],result[i]]}if(result.length>1&&result[0].id===last)result.push(result.shift());return result}
function nextSlide(){const last=slides[slide]?.id;slide++;if(slide>=slides.length&&$('shuffle').checked){slides=shuffleWorks(slides,last);slide=0}showSlide()}
function startTimer(){clearInterval(timer);timer=setInterval(nextSlide,15000);$('slide-pause').textContent='Pause'}
function exit(){clearInterval(timer);timer=null;$('show').hidden=true;if(document.fullscreenElement)document.exitFullscreen().catch(()=>{})}
$('slideshow').onclick=()=>{slides=visible().filter(x=>x.downloaded||x.available_offline);if($('shuffle').checked)slides=shuffleWorks(slides);if(!slides.length)return status('Download artwork first; the slideshow uses only saved images.');slide=0;$('show').hidden=false;showSlide();startTimer()};$('slide-prev').onclick=()=>{slide--;showSlide()};$('slide-next').onclick=nextSlide;$('slide-pause').onclick=()=>{if(timer){clearInterval(timer);timer=null;$('slide-pause').textContent='Play'}else startTimer()};$('exit').onclick=exit;$('full').onclick=()=>{if($('show').requestFullscreen)$('show').requestFullscreen().catch(e=>status(e.message))};document.addEventListener('keydown',e=>{if(e.key==='Escape')exit()});
(async()=>{try{const response=await fetch('/api/museum/config');const config=await response.json();if(!response.ok)throw Error(config.error||'Authorize this browser through the chat first');try{owner=localStorage.getItem('look-museum-owner')||config.owner}catch{owner=config.owner}for(const name of new Set([owner,...config.owners])){const option=document.createElement('option');option.value=name;option.textContent=name;$('owner').append(option)}$('owner').value=owner;await load()}catch(e){status(e.message)}})();
setInterval(async()=>{if(busy||!$('show').hidden)return;try{const data=await api();job(data);if(mode!=='discover'&&data.job?.state==='running'&&!$('query').value){items=data.items;draw()}}catch{}},5000);
</script></body></html>'''
