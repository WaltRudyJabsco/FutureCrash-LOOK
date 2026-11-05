"""Authenticated museum gallery shared by Signal and Albert."""
import json
import base64
import re
from pathlib import Path
import urllib.parse
import urllib.request
import urllib.error
try:from .radio_web import send
except ImportError:from radio_web import send


def print_request(node_url,payload=None):
    """Use the existing local Fabric gateway; browser input never supplies URLs/files."""
    def request(path,value=None):
        req=urllib.request.Request(node_url+path,data=None if value is None else json.dumps(value).encode(),headers={'Content-Type':'application/json'})
        try:
            with urllib.request.urlopen(req,timeout=60) as response:return json.load(response)
        except urllib.error.HTTPError as exc:
            try:detail=json.load(exc).get('error')
            except (ValueError,AttributeError):detail=None
            raise ValueError(detail or 'Print service returned HTTP '+str(exc.code)) from exc
    if payload is not None and not isinstance(payload,dict):raise ValueError('Invalid print request')
    if payload and payload.get('action') in {'send','discard','inspect'}:
        if set(payload)-{'action','node','id','confirm'} or payload.get('confirm') is not True:raise ValueError('Explicit print confirmation required')
        if not re.fullmatch(r'[a-f0-9]{32}',str(payload.get('id',''))):raise ValueError('Invalid print plan')
        return request('/v1/print?'+urllib.parse.urlencode({'target':payload.get('node','local')}),{'action':payload['action'],'ident':payload['id'],'confirm':True})
    catalog=request('/v1/print/fabric')
    def usable(route):return not re.search(r'\b(disabled|paused|unavailable)\b',route.get('status',''),re.I)
    printers=catalog.get('printers',[])
    printers.sort(key=lambda row:not any(usable(r) and r.get('profile',{}).get('kind')=='escpos' for r in row['routes']))
    if payload is None:return {'printers':printers,'errors':catalog.get('errors',[])}
    if payload.get('action')!='prepare' or set(payload)-{'action','id','target','printer','options'}:raise ValueError('Unknown museum print action')
    ident=str(payload.get('id',''))
    if not re.fullmatch(r'(met|aic)-[1-9][0-9]{0,9}',ident):raise ValueError('Invalid artwork')
    matches=[row for row in printers if row['id']==payload.get('printer')]
    if len(matches)!=1:raise ValueError('Select a discovered printer')
    destination=matches[0];routes=[r for r in destination['routes'] if usable(r)]
    if not routes:raise ValueError('Printer is paused or unavailable')
    route=sorted(routes,key=lambda r:(r['node']!=catalog.get('local_node'),r['node'],r['name']))[0]
    url=node_url+'/v1/museum/image?'+urllib.parse.urlencode({'target':payload.get('target','local'),'id':ident})
    with urllib.request.urlopen(url,timeout=45) as response:data=response.read(3*1024*1024+1)
    if not 0<len(data)<=3*1024*1024:raise ValueError('Artwork exceeds the 3 MiB print limit')
    plan=request('/v1/print?'+urllib.parse.urlencode({'target':route['node']}),{'action':'prepare','queue':route['name'],'data':base64.b64encode(data).decode(),'filename':ident+'.jpg','kind':'receipt-image' if route.get('profile',{}).get('kind')=='escpos' else 'document','options_value':payload.get('options',{'copies':1})})
    return dict(plan,destination=destination['label'])


def handle(handler,node_url,payload=None):
    parsed=urllib.parse.urlsplit(handler.path)
    if parsed.path=='/api/museum/print':return send(handler,200,print_request(node_url,payload))
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
    if payload is not None and (parsed.path!='/api/museum' or payload.get('action') not in {'save','pin','sync','favorite','mark-removal','rotation','starter','featured','cancel','collection-create','collection-add','collection-remove'}):raise ValueError('Unknown museum action')
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
:root{color-scheme:light;--paper:#f5f0e6;--ink:#24374a;--muted:#626c72;--line:#d4ccba;--accent:#315c80;--panel:#fffdf7;--brass:#80612c;--brass-wash:#ebe1cd}*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:16px/1.5 system-ui}header,main{max-width:1200px;margin:auto;padding:24px}header{display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid var(--line)}h1{font:38px Georgia,serif;margin:0}h2{font:25px Georgia,serif;margin:12px 0}small,.muted{color:var(--muted)}a{color:var(--accent)}nav,form,.actions{display:flex;align-items:center;flex-wrap:wrap;gap:8px}button,input,select{font:inherit;padding:9px 13px;min-height:44px;border-radius:6px;border:1px solid var(--line);background:var(--panel);color:var(--ink)}button{cursor:pointer}button:disabled{opacity:.5;cursor:default}button.active,button.primary{background:var(--accent);color:white}button:focus-visible,input:focus-visible,select:focus-visible{outline:3px solid #b29151;outline-offset:3px}input[type=search]{flex:1;min-width:150px}#count{width:95px}form{margin:15px 0}#status{min-height:26px;color:var(--muted)}#grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:22px;margin:24px 0}.card{background:var(--panel);border:1px solid var(--line);padding:12px;display:flex;flex-direction:column}.card img{width:100%;height:230px;object-fit:contain;background:#ece7dc}.card .view{border:0;padding:0;background:transparent}.card h2{font-size:20px}.card p{margin:4px 0;font-size:14px}.card .actions{margin-top:auto;padding-top:12px}.card button{font-size:14px}dialog{max-width:min(1000px,96vw);max-height:95dvh;background:var(--paper);color:var(--ink);border:1px solid var(--line);padding:20px}dialog::backdrop{background:#101722df}#large{display:block;max-width:100%;height:55vh;object-fit:contain;margin:auto}#detail-content:fullscreen{background:var(--paper);color:var(--ink);padding:20px;overflow:auto;box-sizing:border-box;width:100vw;max-width:none;height:100dvh;max-height:none}#detail-content:fullscreen #large{height:70dvh}#detail-text{max-width:75ch}#show{position:fixed;inset:0;z-index:20;background:#0c1116;color:#f5f0e6;padding:20px;display:flex;flex-direction:column;align-items:center}#show[hidden]{display:none}#show img{flex:1;min-height:0;max-height:calc(100dvh - 250px);width:100%;object-fit:contain}#show p{margin:10px;max-width:90%;text-align:center}#show .actions{flex:none}#job{padding:12px;border-left:3px solid #b29151;margin:16px 0}#job[hidden]{display:none}@media(max-width:500px){header,main{padding:14px}h1{font-size:30px}#grid{grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}.card{padding:8px}.card img{height:150px}.card h2{font-size:17px}.card .actions{gap:4px}.card button{padding:7px;font-size:12px}dialog{padding:12px}#large{height:42vh}}
header{border-top:4px solid var(--brass)}header small{color:var(--brass);letter-spacing:.14em;font-size:11px}nav{padding-bottom:18px;border-bottom:1px solid var(--line)}nav button.active{background:var(--brass);border-color:var(--brass)}button:hover:not(:disabled){border-color:var(--brass)}#owner-form{padding:14px 0}#owner-form label{font-size:14px;color:var(--muted)}input[type=checkbox],progress{accent-color:var(--brass)}input[type=checkbox]{min-height:0;padding:0;margin:0;width:16px;height:16px;flex:none}.actions>label{display:flex;align-items:center;gap:8px;min-height:44px;font-size:14px}details{padding:14px 18px;background:var(--panel);border:1px solid var(--line);border-radius:8px}summary{cursor:pointer;color:var(--brass)}.card{border-radius:8px;overflow:hidden;box-shadow:0 3px 12px #24374a08}.card img{border-radius:4px}.card h2{line-height:1.25}.card p{color:var(--muted)}.card .actions{border-top:1px solid var(--line);margin-top:14px}.card .actions button{background:transparent;font-size:12px;min-height:36px;padding:6px 9px}#job{background:var(--brass-wash);border-color:var(--brass);border-radius:6px;padding:16px 20px}#job p{margin:6px 0}#job .job-title{font-weight:600;color:var(--brass)}#job details{margin-top:10px;font-size:14px}#job progress{height:10px;width:100%}#status{font-size:14px}#grid>.empty{grid-column:1/-1;padding:36px;text-align:center;border:1px dashed var(--line)}@media(max-width:500px){#owner-form{align-items:stretch}#owner-form label{width:100%}.card .actions button{min-height:44px}}
.actions button[aria-pressed]{min-width:44px;min-height:44px;font-size:20px}.actions button[aria-pressed=true]{background:var(--brass-wash);border-color:var(--brass)}.print-options{display:flex;flex-wrap:wrap;gap:12px 18px}.print-options label{display:flex;flex-direction:column;gap:5px}.print-options input{width:5em}#print-dialog{max-width:min(760px,calc(100vw - 48px))}</style></head><body><header><div><small>LOOK · AN OPEN COLLECTION</small><h1>Museum</h1></div><a href="/">Back to chat</a></header><main>
<nav><button id="saved" class="active">To explore</button><button id="all">All works</button><button id="discover">Discover</button><button id="collections">Collections</button><button id="favorites">Favorites</button><button id="review">Removal review</button><button id="slideshow">Slideshow</button></nav>
<form id="owner-form"><label for="owner">Library owner / downloads go to</label><select id="owner"></select><button>Use library</button><button type="button" id="sync">Keep this view on this host</button></form>
<div class="actions"><select id="collection-choice" aria-label="Named collection" hidden></select><button id="new-collection">New collection</button><button id="featured">Download museum highlights</button><label><input id="rotation" type="checkbox"> Daily refill: 1,000 to explore + Favorites</label><label><input id="offline-only" type="checkbox"> Available offline on this host</label><label><input id="shuffle" type="checkbox"> Shuffle slideshow</label></div><form id="search"><input id="query" type="search" placeholder="Artist, subject, period…" aria-label="Search art"><select id="source" aria-label="Museum source" hidden><option value="met">The Met</option><option value="aic">Art Institute of Chicago</option></select><button class="primary">Search</button></form>
<details><summary>Build starter library</summary><p>Chosen themes across painting, prints, sculpture, photography and decorative arts. Downloads only works marked public domain by the museum. Up to 20 MB per image; 3 GiB collection budget. Saved items are reused.</p><label>Works <input id="count" type="number" min="1" max="1000" value="1000"></label> <button id="starter">Build on selected owner</button></details>
<div id="job" hidden></div><p id="status" role="status" aria-live="polite">Opening the collection…</p><div id="grid"></div><div class="actions"><button id="previous" hidden>Previous page</button><button id="next" hidden>Next page</button></div>
</main><dialog id="print-dialog"><h2>Print artwork</h2><p id="print-title"></p><div class="print-options"><label>Printer <select id="print-printer"></select></label><label>Style <select id="print-style"><option value="image">Image</option><option value="ascii">ASCII</option></select></label><label>Rotation <select id="print-rotation"><option value="0">Original</option><option value="90">90° clockwise</option></select></label><label>Paper allowance <select id="print-allowance"><option value="304.8">Receipt · up to 1 ft</option><option value="3048">Banner · up to 10 ft</option></select></label><label>Copies <input id="print-copies" type="number" min="1" max="20" value="1"></label></div><p id="print-status" role="status"></p><div class="actions"><button id="print-review">Review print</button><button id="print-send" hidden>Print</button><button id="print-check" hidden>Check status</button><button id="print-close">Close</button></div></dialog><dialog id="detail"><div id="detail-content"><div class="actions"><button id="close">Close</button><button id="detail-prev" aria-label="Previous artwork">← Previous</button><button id="detail-next" aria-label="Next artwork">Next →</button><span id="detail-position" class="muted" aria-live="polite"></span></div><button id="detail-full">Fullscreen</button><div id="detail-actions" class="actions"></div><p id="detail-status" role="status"></p><img id="large" alt=""><h2 id="title"></h2><p id="credit"></p><p id="detail-text"></p><a id="origin" target="_blank" rel="noopener">View museum record ↗</a></div></dialog>
<div id="show" hidden><img id="slide-image" alt=""><p id="slide-caption"></p><div id="slide-actions" class="actions"></div><p id="slide-status" role="status"></p><div class="actions"><button id="slide-prev" aria-keyshortcuts="ArrowLeft">← Previous</button><button id="slide-pause" aria-keyshortcuts="Space" title="Space: pause or play">Pause · Space</button><button id="slide-next" aria-keyshortcuts="ArrowRight">Next →</button><button id="full" aria-keyshortcuts="f">Fullscreen · F</button><button id="exit" aria-keyshortcuts="Escape">Exit · Esc</button></div></div>
<script src="/browser-views.js"></script><script>
'use strict';const $=id=>document.getElementById(id);let owner='local',mode='saved',items=[],page=1,more=false,busy=false,slides=[],slide=0,timer=null,requestNumber=0,collections={},collectionId="",offline=false,detailRow=null,detailRows=[],detailIndex=0;
function status(value){$('status').textContent=value;$('detail-status').textContent=value;$('slide-status').textContent=value}
function endpoint(suffix='',extra={}){return '/api/museum'+suffix+'?'+new URLSearchParams({target:owner,...extra})}
async function api(suffix='',payload=null,extra={}){const response=await fetch(endpoint(suffix,extra),{method:payload?'POST':'GET',headers:payload?{'Content-Type':'application/json'}:{},body:payload?JSON.stringify(payload):undefined,signal:AbortSignal.timeout(100000)});const data=await response.json();if(!response.ok||!data.ok)throw Error(data.error||'Museum unavailable');return data}
function imageURL(row){if(offline&&!row.available_offline)return '';return row.downloaded||row.available_offline?endpoint('/image',{id:row.id}):row.image_url}
function safeImage(row){if(!imageURL(row))return '';try{const url=new URL(imageURL(row),location.href);if(url.origin===location.origin||url.protocol==='https:'&&['images.metmuseum.org','www.artic.edu'].includes(url.hostname))return url.href}catch{}return ''}
function open(row){
 // Capture the displayed order so detail navigation stays within this view.
 detailRows=visible().filter(item=>safeImage(item));detailIndex=detailRows.findIndex(item=>item.id===row.id);
 if(detailIndex<0){detailRows=[row];detailIndex=0}showDetail();$('detail').showModal();
}
function moveDetail(direction){if(detailRows.length<2)return;detailIndex=(detailIndex+direction+detailRows.length)%detailRows.length;showDetail()}
function showDetail(){const row=detailRows[detailIndex];detailRow=row;
 $('detail-position').textContent=(detailIndex+1)+' / '+detailRows.length;
 $('detail-prev').disabled=$('detail-next').disabled=detailRows.length<2;renderActions(row,$('detail-actions'));$('detail-status').textContent='';$('large').src=safeImage(row);$('large').alt=row.title;$('title').textContent=row.title;$('credit').textContent=[row.artist,row.date,row.medium,row.museum,'CC0'].filter(Boolean).join(' · ');$('detail-text').textContent=row.description;$('origin').href=row.source==='met'?'https://www.metmuseum.org/art/collection/search/'+row.id.split('-')[1]:'https://www.artic.edu/artworks/'+row.id.split('-')[1];}
$('detail-prev').onclick=()=>moveDetail(-1);$('detail-next').onclick=()=>moveDetail(1);
function updateItems(rows){
 const previous=new Map(items.map(row=>[row.id,row]));
 items=rows.map(row=>{const old=previous.get(row.id);if(!old)return row;for(const key of Object.keys(old))if(!(key in row))delete old[key];return Object.assign(old,row)});
}
function visible(){return items.filter(x=>(mode==='review'?!!x.removal_due:!x.removal_due)&&(mode!=='saved'||!x.favorite)&&(mode!=='favorites'||x.favorite)&&(mode!=='collections'||(x.collections||[]).includes(collectionId))&&(!$('offline-only').checked||x.available_offline))}
function collectionChoices(){const select=$('collection-choice');select.replaceChildren();for(const [id,value] of Object.entries(collections)){const option=document.createElement('option');option.value=id;option.textContent=value.name;select.append(option)}if(!collections[collectionId])collectionId=Object.keys(collections)[0]||'';select.value=collectionId;select.hidden=mode!=='collections'}
let printRow=null,printPlan=null,printAttempted=false,printBusy=false,printEpoch=0,printPoll=null;
function printStatus(result){const pending=['submitting','printing'].includes(result.state);$('print-status').textContent=(pending?'Accepted; waiting for printer delivery. ':'Print '+result.state+'. ')+(result.receipt?.error||result.receipt?.note||result.note||'')}
function watchPrint(plan,epoch){clearTimeout(printPoll);printPoll=setTimeout(async()=>{if(epoch!==printEpoch||!$('print-dialog').open)return;try{const result=await printAPI({action:'inspect',node:plan.node,id:plan.id,confirm:true});if(epoch!==printEpoch)return;printStatus(result);if(['submitting','printing'].includes(result.state))watchPrint(plan,epoch)}catch(e){if(epoch===printEpoch)$('print-status').textContent=e.message+' · Use Check status; do not resend.'}},1500)}
async function printAPI(value){const response=await fetch('/api/museum/print',{method:value?'POST':'GET',headers:value?{'Content-Type':'application/json'}:{},body:value?JSON.stringify(value):undefined});const data=await response.json();if(!response.ok||data.error)throw Error(data.error||'Print unavailable');return data}
async function openPrint(row){
 if(printBusy)return;
 if(document.fullscreenElement)await document.exitFullscreen();
 if(timer){clearInterval(timer);timer=null;$('slide-pause').textContent='Play · Space'}
 const epoch=++printEpoch;printRow={...row};printPlan=null;printAttempted=false;$('print-title').textContent=row.title;$('print-send').hidden=true;$('print-check').hidden=true;$('print-review').disabled=true;$('print-status').textContent='Finding printers…';$('print-dialog').showModal();
 try{const data=await printAPI();if(epoch!==printEpoch)return;$('print-printer').replaceChildren();for(const printer of data.printers){const option=document.createElement('option');option.value=printer.id;option.textContent=printer.label;$('print-printer').append(option)}$('print-review').disabled=!data.printers.length;$('print-status').textContent=data.printers.length?'Choose a printer, then review. Nothing has printed.':'No printers available.'}catch(e){if(epoch===printEpoch)$('print-status').textContent=e.message}
}
async function discardPrint(){if(printPlan&&!printAttempted){const plan=printPlan;printPlan=null;await printAPI({action:'discard',node:plan.node,id:plan.id,confirm:true})}}
for(const id of ['print-printer','print-style','print-rotation','print-copies','print-allowance'])$(id).onchange=()=>{discardPrint().catch(e=>$('print-status').textContent=e.message);$('print-send').hidden=true;$('print-status').textContent='Review this destination before printing.'};
$('print-review').onclick=async()=>{const button=$('print-review');printBusy=true;$('print-close').disabled=true;button.disabled=true;for(const id of ['print-printer','print-style','print-rotation','print-copies','print-allowance'])$(id).disabled=true;try{await discardPrint();printPlan=await printAPI({action:'prepare',target:owner,id:printRow.id,printer:$('print-printer').value,options:{copies:Number($('print-copies').value),style:$('print-style').value,rotation:Number($('print-rotation').value),paper_limit_mm:Number($('print-allowance').value)}});printAttempted=false;$('print-status').textContent=printPlan.destination+' · '+(printPlan.options?.copies??Number($('print-copies').value))+' copies · '+$('print-style').value+' · '+$('print-rotation').value+'° · '+(printPlan.estimated_paper_mm!==undefined?'about '+(printPlan.estimated_paper_mm/10).toFixed(1)+' cm of paper · '+((printPlan.max_paper_mm??250)/10).toFixed(1)+' cm limit':'document printer')+' · Ready for your confirmation.';$('print-send').hidden=false;$('print-send').disabled=false}catch(e){$('print-status').textContent=e.message}finally{printBusy=false;$('print-close').disabled=false;button.disabled=false;for(const id of ['print-printer','print-style','print-rotation','print-copies','print-allowance'])$(id).disabled=false}};
$('print-send').onclick=async()=>{
 if(!printPlan||printAttempted||printBusy)return;
 printAttempted=true;printBusy=true;
 for(const id of ['print-send','print-review','print-printer','print-close','print-style','print-rotation','print-copies','print-allowance'])$(id).disabled=true;
 try{const result=await printAPI({action:'send',node:printPlan.node,id:printPlan.id,confirm:true});printStatus(result);if(['submitting','printing'].includes(result.state))watchPrint(printPlan,printEpoch);$('print-send').hidden=true;$('print-check').hidden=false}
 catch(e){$('print-status').textContent=e.message+' · Check printer jobs before retrying.'}
 finally{printBusy=false;for(const id of ['print-review','print-printer','print-close','print-style','print-rotation','print-copies','print-allowance'])$(id).disabled=false}
};
$('print-check').onclick=async()=>{if(!printPlan||printBusy)return;try{const result=await printAPI({action:'inspect',node:printPlan.node,id:printPlan.id,confirm:true});printStatus(result)}catch(e){$('print-status').textContent=e.message}};
$('print-close').onclick=()=>{if(printBusy)return;printEpoch++;clearTimeout(printPoll);discardPrint().catch(()=>{});$('print-dialog').close()};$('print-dialog').addEventListener('cancel',e=>{if(printBusy){e.preventDefault();return}printEpoch++;clearTimeout(printPoll);discardPrint().catch(()=>{})});
function renderActions(row,controls){
 controls.replaceChildren();function button(label,action,accessible=label,pressed=null){const b=document.createElement('button');b.textContent=label;b.setAttribute('aria-label',accessible);b.title=accessible;if(pressed!==null)b.setAttribute('aria-pressed',String(pressed));b.onclick=async()=>{b.disabled=true;if(timer){clearInterval(timer);timer=null;$('slide-pause').textContent='Play · Space'}try{await action()}catch(e){status(e.message)}finally{b.disabled=false;if(detailRow)renderActions(detailRow,$('detail-actions'));if(!$('show').hidden&&slides.length)renderActions(slides[slide],$('slide-actions'))}};controls.append(b)}
 button('Print',()=>openPrint(row),'Print this artwork');
 if(!offline&&!row.downloaded&&!row.removal_due)button('Save to '+owner,async()=>{await api('',{action:'save',id:row.id});row.downloaded=true;status('Downloaded on '+owner);draw()});
 if(row.downloaded&&!offline){button('👍',async()=>{await api('',{action:'favorite',id:row.id});row.favorite=!row.favorite;if(row.favorite)delete row.removal_due;draw()},row.favorite?'Remove from Favorites':'Add to Favorites',!!row.favorite);if(owner!=='local')button('Keep on this host',async()=>{await api('',{action:'pin',id:row.id});status('Copied to this browser host for offline use—not to the phone/browser storage.')})}
 if(row.downloaded&&!offline&&Object.keys(collections).length){button(mode==='collections'?'Remove from collection':'Add to collection',async()=>{
 let id=collectionId;if(mode!=='collections'){const keys=Object.keys(collections);const choice=prompt(keys.map((key,n)=>(n+1)+': '+collections[key].name).join('\n')+'\nChoose collection number');if(choice===null)return;id=keys[Number(choice)-1];if(!id)return}
 await api('',{action:mode==='collections'?'collection-remove':'collection-add',id:row.id,collection:id});const membership=new Set(row.collections||[]);if(mode==='collections')membership.delete(id);else membership.add(id);row.collections=[...membership];draw()
 })}
 if(row.downloaded&&!offline||row.removal_due&&!offline)button(row.removal_due?'↶':'👎',async()=>{const result=await api('',{action:'mark-removal',id:row.id});const updated=result.items?.find(x=>x.id===row.id);if(updated){delete row.removal_due;delete row.removed_at;Object.assign(row,updated)}status(row.removal_due?'Removal scheduled for '+new Date(row.removal_due*1000).toLocaleString():'Removal cancelled');draw()},row.removal_due?'Undo removal':'Thumbs down · remove in 48h',!!row.removal_due);
}
// Keep image elements mounted: image responses are private/no-store, so replacing
// the grid on every progress tick would download every visible image again.
function draw(){
 const grid=$('grid'),rows=visible(),existing=new Map([...grid.querySelectorAll('.card')].map(card=>[card.dataset.id,card]));
 grid.querySelector('.empty')?.remove();
 rows.forEach((row,index)=>{
  let card=existing.get(row.id);existing.delete(row.id);
  if(!card){card=document.createElement('article');card.className='card';card.dataset.id=row.id;
   const view=document.createElement('button');view.className='view';const image=document.createElement('img');image.loading='lazy';view.append(image);view.onclick=()=>open(card.row);card.append(view,document.createElement('h2'));
   for(let n=0;n<3;n++)card.append(document.createElement('p'));
   const controls=document.createElement('div');controls.className='actions';card.append(controls);
  }
  card.row=row;
  const signature=JSON.stringify([row,owner,offline,mode,collectionId,collections]);
  if(card.signature!==signature){
   card.signature=signature;const view=card.querySelector('.view'),image=view.firstChild,url=safeImage(row);
   if(image.getAttribute('src')!==url){if(url)image.src=url;else image.removeAttribute('src')}
   image.hidden=!url;view.disabled=!url;image.alt=row.title;view.setAttribute('aria-label','View '+row.title);card.querySelector('h2').textContent=row.title;
   const captions=[[row.artist,row.date].filter(Boolean).join(' · '),row.museum,offline?(row.available_offline?'Cached image available on this host':'Original unavailable offline'):(row.removal_due?(row.removed_at?'Removed from owner; undo to allow downloading again':'Removal due '+new Date(row.removal_due*1000).toLocaleString()):row.available_offline?'Available on this host; owner '+owner:row.downloaded?'Saved on '+owner:'Online · not saved')];
   card.querySelectorAll('p').forEach((p,n)=>p.textContent=captions[n]);renderActions(row,card.querySelector('.actions'));
  }
  if(grid.children[index]!==card)grid.insertBefore(card,grid.children[index]||null);
 });
 for(const card of existing.values())card.remove();
 if(!rows.length){const empty=document.createElement('p');empty.className='empty';empty.textContent=mode==='discover'?'No open-access images found. Try another subject or museum.':mode==='saved'?'Your discovery pool is empty. Favorites stay saved separately; daily refill can add new artwork.':mode==='favorites'?'Use 👍 on an artwork to save it here.':mode==='collections'?'This collection is empty. Save works to Library, then add them to a collection.':'No matching works. Try Library, Discover, or turn off the offline filter.';grid.append(empty)}
 $('previous').hidden=mode!=='discover'||page<=1;$('next').hidden=mode!=='discover'||!more;
}
let jobSignature='';
function job(data){
 const value=data.job||{},signature=JSON.stringify(value);if(signature===jobSignature)return;jobSignature=signature;
 const panel=$('job');panel.hidden=!value.state;panel.replaceChildren();if(!value.state)return;
 const running=value.state==='running',saved=Number(value.saved)||0,requested=Number(value.requested)||0;
 const labels={running:'Downloading artwork',complete:'Download complete',partial:'Download finished below target',cancelled:'Download cancelled',interrupted:'Download interrupted'};
 const title=document.createElement('p');title.className='job-title';title.textContent=labels[value.state]||'Download '+value.state;panel.append(title);
 if(running){const bar=document.createElement('progress');bar.max=Math.max(1,requested);bar.value=Math.max(0,saved);bar.setAttribute('aria-label','Artwork download progress');panel.append(bar)}
 const count=document.createElement('p');count.textContent=saved.toLocaleString()+' of '+requested.toLocaleString()+' requested works'+(running?' · '+(value.theme||'Preparing'):' · No download is currently running.');panel.append(count);
 if(value.state==='partial'){const note=document.createElement('p');note.textContent='The requested count is a target, not a guarantee. Available source results or download limits can leave a smaller collection.';panel.append(note)}
 if(value.counts){const sources=document.createElement('p');sources.textContent=Object.entries(value.counts).map(([name,count])=>name+': '+count).join(' · ');panel.append(sources)}
 if(value.errors?.length){const details=document.createElement('details'),summary=document.createElement('summary'),note=document.createElement('p');summary.textContent='Source details';note.textContent=value.errors.at(-1);details.append(summary,note);panel.append(details)}
 if(running){const b=document.createElement('button');b.textContent='Stop download';b.onclick=async()=>{b.disabled=true;try{job(await api('',{action:'cancel'}));status('Download stop requested')}catch(e){status(e.message);b.disabled=false}};panel.append(b)}
}
async function load(){const serial=++requestNumber;busy=true;status(mode==='discover'?'Searching museum records…':'Loading saved collection…');try{const data=await api(mode==='discover'?'/search':'',null,mode==='discover'?{q:$('query').value,source:$('source').value,page}:{q:$('query').value});if(serial!==requestNumber)return;updateItems(data.items);more=data.more;offline=!!data.offline;collections=data.collections||collections;collectionChoices();job(data);draw();$('new-collection').disabled=offline;$('starter').disabled=offline;$('featured').disabled=offline;$('rotation').disabled=offline;$('rotation').checked=!!data.rotation?.enabled;status(items.length+' works · '+(offline?'Owner offline; cached catalog · '+data.offline_count+' images on this host':mode==='discover'?'Online museum search':'Library on '+owner))}catch(e){if(serial===requestNumber){if(mode==='discover'){items=[];draw()}status(e.message)}}finally{if(serial===requestNumber)busy=false}}
function switchMode(value){mode=value;page=1;$('source').hidden=value!=='discover';$('collection-choice').hidden=value!=='collections';for(const id of ['saved','all','discover','collections','favorites','review'])$(id).classList.toggle('active',id===value);if(value==='discover'&&!$('query').value)$('query').value='landscape';load()}
$('all').onclick=()=>switchMode('all');$('saved').onclick=()=>switchMode('saved');$('collections').onclick=()=>switchMode('collections');$('collection-choice').onchange=()=>{collectionId=$('collection-choice').value;draw()};$('offline-only').onchange=draw;$('new-collection').onclick=async()=>{const name=prompt('New collection name on '+owner);if(!name)return;try{const data=await api('',{action:'collection-create',name});collectionId=data.active_collection;switchMode('collections')}catch(e){status(e.message)}};$('discover').onclick=()=>switchMode('discover');$('favorites').onclick=()=>switchMode('favorites');$('review').onclick=()=>switchMode('review');$('detail-full').onclick=()=>{if(document.fullscreenElement)document.exitFullscreen().catch(e=>status(e.message));else if($('detail-content').requestFullscreen)$('detail-content').requestFullscreen().catch(e=>status(e.message));else status('Fullscreen is unavailable in this browser')};$('search').onsubmit=e=>{e.preventDefault();page=1;load()};$('previous').onclick=()=>{page--;load()};$('next').onclick=()=>{page++;load()};$('close').onclick=()=>$('detail').close();
$('owner-form').onsubmit=e=>{e.preventDefault();exit();owner=$('owner').value;try{localStorage.setItem('look-museum-owner',owner)}catch{}page=1;items=[];collections={};collectionId='';offline=false;collectionChoices();draw();load()};
$('sync').onclick=async()=>{if(owner==='local')return status('These works are already on the browser host.');const ids=visible().filter(x=>x.downloaded).map(x=>x.id);if(!ids.length)return status('No saved works in this view to copy.');if(!confirm('Keep '+ids.length+' works from this view on the computer hosting this page? Source: '+owner+'. This does not download to your phone/tablet.'))return;try{const result=await api('',{action:'sync',ids});job(result);status('Copying this view to the browser host. Library owner remains '+owner+'.')}catch(e){status(e.message)}};
$('rotation').onchange=async()=>{const enabled=$('rotation').checked;if(enabled&&!confirm('Enable daily refill on '+owner+'? Keep about 1000 undecided works in addition to Favorites, add at most 100 new works/day, skip rejected artwork, preserve favorites and existing collections.')){$('rotation').checked=false;return}try{await api('',{action:'rotation',enabled});status('Daily refill '+(enabled?'enabled':'disabled')+' on '+owner)}catch(e){$('rotation').checked=!enabled;status(e.message)}};
$('featured').onclick=async()=>{if(!confirm('Download up to 500 Met Highlights and 500 Art Institute Featured works on '+owner+'? These are museum selections, not visitor popularity rankings. Existing images are reused; 3 GiB total budget.'))return;try{job(await api('',{action:'featured',count:500,source:'both'}));status('Museum selections downloading on '+owner)}catch(e){status(e.message)}};
$('starter').onclick=async()=>{const count=Number($('count').value);if(!Number.isInteger(count)||count<1||count>1000)return status('Choose 1–1000 works');if(!confirm('Download up to '+count+' open-access artworks on '+owner+'? The collection has a 3 GiB budget; existing works are reused.'))return;try{job(await api('',{action:'starter',count}));status('Starter download running on '+owner)}catch(e){status(e.message)}};
function showSlide(){if(!slides.length)return;renderActions(slides[(slide+slides.length)%slides.length],$('slide-actions'));slide=(slide+slides.length)%slides.length;const row=slides[slide];$('slide-image').src=safeImage(row);$('slide-image').alt=row.title;$('slide-caption').textContent=[row.title,row.artist,row.date,row.museum].filter(Boolean).join(' · ')}
function shuffleWorks(rows,last=''){const result=[...rows];for(let i=result.length-1;i>0;i--){const j=Math.floor(Math.random()*(i+1));[result[i],result[j]]=[result[j],result[i]]}if(result.length>1&&result[0].id===last)result.push(result.shift());return result}
function nextSlide(){const last=slides[slide]?.id;slides=slides.filter(row=>!row.removal_due);if(!slides.length){exit();status('No kept works remain in this slideshow');return}slide=slides.findIndex(row=>row.id===last);slide++;if(slide>=slides.length&&$('shuffle').checked){slides=shuffleWorks(slides,last);slide=0}showSlide()}
function startTimer(){clearInterval(timer);timer=setInterval(nextSlide,15000);$('slide-pause').textContent='Pause · Space'}
function exit(){clearInterval(timer);timer=null;$('show').hidden=true;if(document.fullscreenElement)document.exitFullscreen().catch(()=>{})}
$('slideshow').onclick=()=>{slides=visible().filter(x=>x.downloaded||x.available_offline);if($('shuffle').checked)slides=shuffleWorks(slides);if(!slides.length)return status('Download artwork first; the slideshow uses only saved images.');slide=0;$('show').hidden=false;showSlide();startTimer()};$('slide-prev').onclick=()=>{slide--;showSlide()};$('slide-next').onclick=nextSlide;$('slide-pause').onclick=()=>{if(timer){clearInterval(timer);timer=null;$('slide-pause').textContent='Play · Space'}else startTimer()};$('exit').onclick=exit;$('full').onclick=()=>{if(document.fullscreenElement){document.exitFullscreen().catch(e=>status(e.message));return}if($('show').requestFullscreen)$('show').requestFullscreen().catch(e=>status(e.message))};document.addEventListener('keydown',e=>{if($('print-dialog').open)return;if(e.key==='Escape')exit();
 if(e.code==='Space'&&!$('show').hidden&&!['INPUT','SELECT','TEXTAREA'].includes(e.target.tagName)&&!e.target.isContentEditable){e.preventDefault();if(!e.repeat)$('slide-pause').click();return}
 if(!['INPUT','SELECT','TEXTAREA'].includes(e.target.tagName)&&!e.target.isContentEditable&&(e.key==='ArrowLeft'||e.key==='ArrowRight')){
  if($('detail').open){e.preventDefault();moveDetail(e.key==='ArrowRight'?1:-1)}
  else if(!$('show').hidden){e.preventDefault();$(e.key==='ArrowRight'?'slide-next':'slide-prev').click()}
 }
 if(e.key.toLowerCase()==='f'&&!['INPUT','SELECT','TEXTAREA'].includes(e.target.tagName)){if($('detail').open)$('detail-full').click();else if(!$('show').hidden)$('full').click()}});
(async()=>{try{const response=await fetch('/api/museum/config');const config=await response.json();if(!response.ok)throw Error(config.error||'Authorize this browser through the chat first');try{owner=localStorage.getItem('look-museum-owner')||config.owner}catch{owner=config.owner}for(const name of new Set([owner,...config.owners])){const option=document.createElement('option');option.value=name;option.textContent=name;$('owner').append(option)}$('owner').value=owner;await load()}catch(e){status(e.message)}})();
const PROGRESS_POLL_MS=5000;let polling=false;
async function pollMuseum(){
 if(polling||busy||document.hidden||!$('show').hidden||$('detail').open)return;
 const serial=requestNumber,currentOwner=owner;polling=true;
 try{const data=await api();if(serial!==requestNumber||owner!==currentOwner)return;job(data);
  if(mode!=='discover'&&!$('query').value){updateItems(data.items);offline=!!data.offline;
   const nextCollections=data.collections||collections;
   if(JSON.stringify(collections)!==JSON.stringify(nextCollections)){collections=nextCollections;collectionChoices()}
   draw();
  }
 }catch(e){status('Progress unavailable: '+e.message)}finally{polling=false}
}
setInterval(pollMuseum,PROGRESS_POLL_MS);
</script></body></html>'''
