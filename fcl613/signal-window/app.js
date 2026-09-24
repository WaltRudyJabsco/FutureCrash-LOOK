const N=256;
const main=document.querySelector('main'),A=document.querySelector('#ambient'),a=A.getContext('2d'),C=document.querySelector('#signal'),c=C.getContext('2d');
const log=document.querySelector('#log'),form=document.querySelector('#form'),input=document.querySelector('#input'),drops=document.querySelector('#drops'),decisionPanel=document.querySelector('#decisionPanel'),mediaPanel=document.querySelector('#mediaPanel'),statusEl=document.querySelector('#status'),activity=document.querySelector('#activity'),activityText=document.querySelector('#activityText'),fabricLight=document.querySelector('#fabricLight'),cameraButton=document.querySelector('#cameraButton'),cameraInput=document.querySelector('#cameraInput');
const authGate=document.querySelector('#authGate'),authCode=document.querySelector('#authCode'),authCodeInline=document.querySelector('#authCodeInline');
let endpointAuthorized=false;
async function pollEndpointAuth(){try{const r=await fetch('/api/auth/status',{cache:'no-store'}),d=await r.json();if(d.authorized){endpointAuthorized=true;authGate.hidden=true;form?.removeAttribute('aria-disabled');return}endpointAuthorized=false;authGate.hidden=false;const code=String(d.pending?.code||'------');authCode.textContent=code;authCodeInline.textContent=code;form?.setAttribute('aria-disabled','true')}catch{authGate.hidden=false}setTimeout(pollEndpointAuth,1500)}
pollEndpointAuth();
const signalSession=localStorage.getItem('signal-session')||crypto.randomUUID();
localStorage.setItem('signal-session',signalSession);
a.imageSmoothingEnabled=c.imageSmoothingEnabled=false;
let files=[],energy=.22,mood='quiet',particles=[],artQuietUntil=0,visualTurn=0;
let art={mode:'display',hold:75,fade:25,born:0,fadeStart:0,persist:false};
for(let i=0;i<260;i++)particles.push({x:Math.random()*N,y:Math.random()*N,v:3+Math.random()*12,p:Math.random()*12|0});

let events=[];
function event(text,busy=false){
 const stamp=new Date().toLocaleTimeString([],{hour:'2-digit',minute:'2-digit',second:'2-digit'});
 events.push(`${stamp} ${String(text).toUpperCase()}`); if(events.length>8)events.shift();
 activityText.textContent=events.join('  →  ');
 activity.classList.toggle('busy',busy);
 activity.scrollLeft=activity.scrollWidth;
}
function line(cls,text){const near=log.scrollHeight-log.scrollTop-log.clientHeight<80,d=document.createElement('div');d.className=cls;d.textContent=text;log.append(d);if(near)log.scrollTop=log.scrollHeight}
function col(x){return /^#[0-9a-f]{6}$/i.test(x||'')?x:'#8fd6a2'} const q=n=>Math.max(0,Math.min(255,Number(n)||0));
function pts(arr){return (arr||[]).map(p=>[q(p[0]),q(p[1])])}
function stroke(color,width=1){c.strokeStyle=col(color);c.lineWidth=Math.max(.5,Math.min(16,Number(width)||1));c.lineCap='round';c.lineJoin='round'}

let last=performance.now(),acc=0; const DT=1/30;
function sim(dt){const quiet=performance.now()<artQuietUntil?.6:1;for(const p of particles){p.y+=p.v*dt*(.35+energy*1.7)*quiet;if(p.y>N+8){p.y=-8;p.x=Math.random()*N}if(Math.random()<dt*(1+energy*3))p.p=(p.p+1)%12}}
function render(){a.fillStyle='rgba(2,5,3,.20)';a.fillRect(0,0,N,N);const chars='01:+*·SIGNAL?';a.font='10px monospace';const quiet=performance.now()<artQuietUntil?.38:1;
 for(const p of particles){a.fillStyle=`rgba(105,190,125,${(.12+energy*.32+Math.random()*.08)*quiet})`;a.fillText(chars[p.p%chars.length],p.x,p.y)}}
function frame(t){acc+=Math.min(.1,(t-last)/1000);last=t;while(acc>=DT){sim(DT);acc-=DT}render();requestAnimationFrame(frame)}requestAnimationFrame(frame);

function state(s){if(!s)return;energy=Math.max(0,Math.min(1,Number(s.energy??energy)));mood=s.mood||mood}
function lifetime(d){
 d=d||{};const mode=['moment','display','persist'].includes(d.mode)?d.mode:'display';
 const defaults=mode==='moment'?[15,12]:mode==='persist'?[0,0]:[75,25];
 const minHold=mode==='moment'?12:mode==='display'?45:0;
 const requestedHold=Number(d.hold);
 const requestedFade=Number(d.fade);
 return {mode,hold:mode==='persist'?0:Math.max(minHold,Math.min(300,Number.isFinite(requestedHold)&&requestedHold>0?requestedHold:defaults[0])),
         fade:mode==='persist'?0:Math.max(8,Math.min(120,Number.isFinite(requestedFade)&&requestedFade>0?requestedFade:defaults[1])),
         persist:mode==='persist'};
}
function pathPoly(p,close=false){if(!p.length)return false;c.beginPath();c.moveTo(...p[0]);for(const x of p.slice(1))c.lineTo(...x);if(close)c.closePath();return true}

async function archiveSignal(scene){
 try{
  const snap=document.createElement('canvas');snap.width=N;snap.height=N;
  const x=snap.getContext('2d');x.imageSmoothingEnabled=false;
  x.fillStyle='#020503';x.fillRect(0,0,N,N);x.drawImage(A,0,0);x.drawImage(C,0,0);
  const image=snap.toDataURL('image/png');
  const r=await fetch('/api/snapshot',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({image,scene})});
  const d=await r.json();
  if(r.ok&&d.saved)event('GALLERY SAVED · '+d.saved);
 }catch(err){event('GALLERY ERROR · '+err.message)}
}

function draw(s){if(!s)return;state(s.state);art={...lifetime(s.display),born:performance.now(),fadeStart:0};
 if(s.clear){c.fillStyle=col(s.clear);c.fillRect(0,0,N,N)}
 for(const o of (s.ops||[]).slice(0,512)){try{const k=o[0];
  if(k==='pixel'){c.fillStyle=col(o[3]);c.fillRect(q(o[1]),q(o[2]),1,1)}
  else if(k==='line'){stroke(o[5],o[6]);c.beginPath();c.moveTo(q(o[1]),q(o[2]));c.lineTo(q(o[3]),q(o[4]));c.stroke()}
  else if(k==='rect'){c.fillStyle=col(o[5]);stroke(o[5],o[7]);o[6]?c.fillRect(q(o[1]),q(o[2]),o[3],o[4]):c.strokeRect(q(o[1]),q(o[2]),o[3],o[4])}
  else if(k==='circle'){c.fillStyle=col(o[4]);stroke(o[4],o[6]);c.beginPath();c.arc(q(o[1]),q(o[2]),Math.max(0,o[3]),0,Math.PI*2);o[5]?c.fill():c.stroke()}
  else if(k==='ellipse'){c.fillStyle=col(o[5]);stroke(o[5],o[7]);c.beginPath();c.ellipse(q(o[1]),q(o[2]),Math.max(0,o[3]),Math.max(0,o[4]),0,0,Math.PI*2);o[6]?c.fill():c.stroke()}
  else if(k==='poly'){let p=pts(o[1]);c.fillStyle=col(o[2]);stroke(o[2],o[4]);if(pathPoly(p,true))o[3]?c.fill():c.stroke()}
  else if(k==='polyline'){let p=pts(o[1]);stroke(o[2],o[3]);if(pathPoly(p,false))c.stroke()}
  else if(k==='bezier'){stroke(o[9],o[10]);c.beginPath();c.moveTo(q(o[1]),q(o[2]));c.bezierCurveTo(q(o[3]),q(o[4]),q(o[5]),q(o[6]),q(o[7]),q(o[8]));c.stroke()}
  else if(k==='text'){c.font=`${Math.max(6,Math.min(48,Number(o[5])||12))}px monospace`;c.fillStyle=col(o[3]);c.fillText(String(o[4]).slice(0,42),q(o[1]),q(o[2]))}
  else if(k==='pulse'){stroke(o[4],1);for(let r=Math.max(1,o[3]-8);r<=o[3]+8;r+=8){c.beginPath();c.arc(q(o[1]),q(o[2]),r,0,Math.PI*2);c.stroke()}}
  else if(k==='dither'){const [x,y,w,h,ca,cb,d]=o.slice(1);for(let yy=0;yy<h;yy+=2)for(let xx=0;xx<w;xx+=2){c.fillStyle=Math.random()<(Number(d)||.5)?col(ca):col(cb);c.fillRect(q(x+xx),q(y+yy),2,2)}}
  else if(k==='noise'){c.fillStyle=col(o[5]);const amount=Math.min(2000,Math.max(0,Number(o[6])||100));for(let i=0;i<amount;i++)c.fillRect(q(o[1]+Math.random()*o[3]),q(o[2]+Math.random()*o[4]),1,1)}
 }catch{}}
 artQuietUntil=performance.now()+Math.max(4500,Math.min(10000,art.hold*300));
 event(`SIGNAL DRAW · ${art.persist?'PERSIST':Math.round(art.hold)+'S HOLD + '+Math.round(art.fade)+'S FADE'}`);
 requestAnimationFrame(()=>requestAnimationFrame(()=>archiveSignal(s)));
}
setInterval(()=>{
 if(!art.born || art.persist)return;
 const age=(performance.now()-art.born)/1000;
 if(age < art.hold)return;
 if(!art.fadeStart)art.fadeStart=performance.now();
 const alpha=Math.min(.08, 1/(Math.max(1,art.fade)*8));
 c.save();c.globalCompositeOperation='destination-out';c.fillStyle=`rgba(0,0,0,${alpha})`;c.fillRect(0,0,N,N);c.restore();
 if((performance.now()-art.fadeStart)/1000 >= art.fade){c.clearRect(0,0,N,N);art.born=0;event('SIGNAL FADED · READY')}
},125);

function layout(){const r=main.getBoundingClientRect(),w=r.width,h=r.height;let mode,size;
 if(w>h*1.18){mode=h<350?'compact':'wide';size=Math.floor(Math.min(h-(mode==='compact'?16:46),w*.38,420))}
 else {mode='stacked';size=Math.floor(Math.min(w-24,h*.43,420))}
 size=Math.max(96,size);main.classList.remove('mode-wide','mode-stacked','mode-compact');main.classList.add('mode-'+mode);main.style.setProperty('--signal-size',size+'px')}
new ResizeObserver(layout).observe(main);addEventListener('resize',layout);requestAnimationFrame(layout);

async function status(){try{const d=await(await fetch('/api/status')).json();statusEl.textContent=d.mode==='lo'?(d.lo?'LO':'LO !'):(d.ok?'OLLAMA':'OFFLINE');statusEl.title=JSON.stringify(d)}catch{statusEl.textContent='OFFLINE'}}status();
function chips(){drops.innerHTML='';for(const [i,f] of files.entries()){const x=document.createElement('span');x.className='chip'+(f.type?.startsWith('image/')?' image-chip':'');if(f.type?.startsWith('image/')&&f.encoding==='base64'){const img=document.createElement('img');img.className='chip-thumb';img.alt='';img.src=`data:${f.type||'image/jpeg'};base64,${f.content}`;x.append(img)}const label=document.createElement('span');label.textContent=f.path||f.name;x.append(label);x.title='Attached · tap to remove';x.onclick=()=>{files.splice(i,1);chips();input.focus()};drops.append(x)}}
function imageBase64(file){return new Promise((resolve,reject)=>{const r=new FileReader();r.onerror=()=>reject(r.error||new Error('photo read failed'));r.onload=()=>{const value=String(r.result||'');const comma=value.indexOf(',');resolve(comma>=0?value.slice(comma+1):value)};r.readAsDataURL(file)})}
async function fileObj(file,path=file.name){
 if(file.type?.startsWith('image/')){if(file.size>12_000_000)throw Error('image is larger than 12 MB');return{name:file.name,path,size:file.size,type:file.type,encoding:'base64',content:await imageBase64(file)}}
 let content='';if(file.size<1_000_000){try{content=await file.text()}catch{content='[binary/unreadable]'}}else content=`[file omitted: ${file.size} bytes]`;return{name:file.name,path,size:file.size,type:file.type,content}
}
async function walk(entry,prefix=''){if(entry.isFile)return new Promise(r=>entry.file(async f=>r([await fileObj(f,prefix+f.name)])));if(entry.isDirectory){const rd=entry.createReader(),out=[];while(true){const b=await new Promise(r=>rd.readEntries(r));if(!b.length)break;for(const e of b)out.push(...await walk(e,prefix+entry.name+'/'))}return out}return[]}
cameraButton?.addEventListener('click',()=>cameraInput?.click());
cameraInput?.addEventListener('change',async()=>{const f=cameraInput.files?.[0];if(!f)return;try{const obj=await fileObj(f,f.name||`signal-camera-${Date.now()}.jpg`);files.push(obj);files=files.slice(-20);chips();event('CAMERA · PHOTO ATTACHED');if(!input.value.trim()){input.value='what am I looking at?';input.focus();input.select()}else input.focus()}catch(err){event('CAMERA ERROR · '+err.message)}finally{cameraInput.value=''}});
addEventListener('dragover',e=>{e.preventDefault();document.body.classList.add('drag')});addEventListener('dragleave',()=>document.body.classList.remove('drag'));addEventListener('drop',async e=>{e.preventDefault();document.body.classList.remove('drag');const out=[];for(const item of e.dataTransfer.items||[]){const en=item.webkitGetAsEntry?.();if(en)out.push(...await walk(en));else{const f=item.getAsFile?.();if(f)out.push(await fileObj(f))}}files=out.slice(0,20);chips();input.focus()});
form.addEventListener('submit',async e=>{e.preventDefault();if(!endpointAuthorized)return;const text=input.value.trim();if(!text&&!files.length)return;line('user','› '+(text||`[${files.length} dropped item${files.length===1?'':'s'}]`));input.value='';input.placeholder='say something · drop files';const sent=files;files=[];chips();
 if(/^\/(help|lk)$/i.test(text)){line('assistant','Signal commands: /help · /clear · /status · /gallery · /player. Media output lives on the active player card; This Device streams to the current browser. CAM attaches an iPhone/rear-camera photo; Return accepts the prefilled vision prompt or typing replaces it. Everything else goes to LO.');return}
 if(/^\/clear$/i.test(text)){log.innerHTML='';c.clearRect(0,0,N,N);art.born=0;fetch('/api/session/clear',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({session:signalSession})}).catch(()=>{});event('CLEARED');return}
 if(/^\/status$/i.test(text)){status();line('system',statusEl.title||statusEl.textContent);return}
 if(/^\/gallery$/i.test(text)){try{const d=await(await fetch('/api/status')).json();line('system','Gallery: '+(d.gallery||'disabled'))}catch{line('system','Gallery unavailable')}return}
 if(/^\/player$/i.test(text)){mediaDismissed=false;await pollMedia(true);return}
 energy=.65;event('LO REQUEST',true);
 try{const r=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text,files:sent,visual:false,session:signalSession,media_node:mediaNode,media_endpoint:selectedMediaOutput})});const d=await r.json();if(!r.ok||d.error)throw Error(d.error||r.statusText);
 if(d.media&&selectedMediaOutput==='browser'&&Array.isArray(d.media.queue)&&d.media.queue.length){
   const source=String(d.media.node||mediaNode||'');
   browserMedia={active:false,sourceNode:source,index:Number(d.media.index||0),queue:d.media.queue.slice(),state:'loading',position:0,duration:0};
   mediaDismissed=false;await browserPlayIndex(browserMedia.index);
   if(source){fetch('/api/media/control',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action:'stop',node:source})}).then(x=>{if(!x.ok)event('MEDIA WARNING · source stop failed')}).catch(()=>event('MEDIA WARNING · source stop failed'))}
 }
 if(d.text)line('assistant',d.text);if(Array.isArray(d.lo_events) && d.lo_events.length){
   for(const e of d.lo_events){
     const raw=String(e.event||'');
     const name=raw.replaceAll('_',' ');
     if(!name)continue;
     if(raw==='source_receipt'){
       const bits=[e.edge,e.source,e.confidence,e.as_of?('as of '+e.as_of):''].filter(Boolean);
       line('system','source › '+bits.join(' · '));
     }
     let detail=e.model||e.tool||e.tokens||e.message||e.edge||'';
     event(`LO ${name}${detail?' · '+detail:''}`);
   }
 } else event('LO RESPONSE');
 if(Array.isArray(d.artifacts))for(const x of d.artifacts){
   if(String(x.type||'').startsWith('image/')){const img=document.createElement('img');img.src=x.url;img.alt=x.name;img.className='artifact-image';log.append(img)}
   const a=document.createElement('a');a.href=x.url;a.target='_blank';a.rel='noopener';a.textContent='↗ '+x.name;a.className='artifact';log.append(a);event('ARTIFACT READY · '+x.name)}
 const myTurn=++visualTurn;
 if(text||d.text){event('SIGNAL COMPOSE',true);fetch('/api/visual',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text,answer:d.text||'',events:d.lo_events||[]})}).then(r=>r.json()).then(vd=>{
   if(myTurn!==visualTurn)return;const vk=vd?.visual?.kind;
   if(vk==='draw'){const src=vd.visual.scene_source||'unknown',kind=vd.visual.fallback_kind||'';event(vd.visual.fallback?`SIGNAL FALLBACK · ${kind||src}`:`SIGNAL RESPONSE · ${src}`);draw(vd.signal)}
   else if(vk==='error')event('SIGNAL ERROR · '+(vd.visual.error||'UNKNOWN'));
 }).catch(err=>event('SIGNAL ERROR · '+err.message))}
 event('READY');pollMedia(true);energy=Math.max(.25,energy*.65)}
 catch(err){event('ERROR · '+err.message);line('error','! '+err.message);energy=.15}});

let mediaNode='',mediaOutputs=[],lastMediaState=null,nodeMediaState=null;
const browserAudio=new Audio();browserAudio.preload='metadata';
let browserMedia={active:false,sourceNode:'',index:0,queue:[],state:'stopped',position:0,duration:0};
let selectedMediaOutput='browser',mediaHandoff=false,mediaPickerActive=false;
function thisDeviceLabel(){return /iPhone/i.test(navigator.userAgent)?'This iPhone':/iPad/i.test(navigator.userAgent)?'This iPad':'This Device'}
function nodeTarget(node){return `node:${String(node||'')}`}
function targetNode(target){return String(target||'').startsWith('node:')?String(target).slice(5):''}
async function pollMediaOutputs(){try{const r=await fetch('/api/media/outputs',{cache:'no-store'});if(!r.ok)return;const d=await r.json();mediaOutputs=Array.isArray(d.outputs)?d.outputs:[];
 // Browser endpoints belong to themselves by default. A Fabric node becomes the
 // output only after the user explicitly chooses it in OUT for this page session.
 if(selectedMediaOutput==='browser')return;
 const selected=targetNode(selectedMediaOutput)||mediaNode;
 if(selected&&mediaOutputs.some(x=>String(x.node||'')===selected)){mediaNode=selected;selectedMediaOutput=nodeTarget(selected);return}
 selectedMediaOutput='browser';mediaNode=''
}catch{}}
let mediaDismissed=false,mediaExpanded=false,lastMediaKey='';
function mediaTime(v){v=Number(v);if(!Number.isFinite(v)||v<0)return '--:--';v=Math.floor(v);return v>=3600?`${Math.floor(v/3600)}:${String(Math.floor(v%3600/60)).padStart(2,'0')}:${String(v%60).padStart(2,'0')}`:`${Math.floor(v/60)}:${String(v%60).padStart(2,'0')}`}
function mediaButton(label,title,action,index=null){const b=document.createElement('button');b.type='button';b.className='media-button';b.textContent=label;b.title=title;b.onclick=()=>mediaControl(action,index);return b}
function browserSnapshot(){const queue=browserMedia.queue||[],index=Math.max(0,Math.min(browserMedia.index,Math.max(0,queue.length-1)));return{available:true,active:browserMedia.active,state:browserMedia.state,index,count:queue.length,queue,entry:queue[index]||{},position:browserAudio.currentTime||0,duration:browserAudio.duration||0,node:'browser',output_id:'browser'}}
async function browserPlayIndex(index){const queue=browserMedia.queue||[];if(!queue.length)throw Error('browser queue is empty');index=Math.max(0,Math.min(Number(index)||0,queue.length-1));browserMedia.index=index;const entry=queue[index]||{};const itemId=String(entry.id||entry.digest||'');browserAudio.src=`/api/media/audio?node=${encodeURIComponent(browserMedia.sourceNode)}&id=${encodeURIComponent(itemId)}&index=${index}&t=${Date.now()}`;browserAudio.load();await browserAudio.play();browserMedia.active=true;browserMedia.state='playing';renderMedia(browserSnapshot(),true)}
async function selectMediaOutput(next,selectEl){const previous=selectedMediaOutput;if(!next||next===previous)return;const sourceState=nodeMediaState;
 try{
  if(next==='browser'){
   if(!sourceState?.queue?.length)throw Error('no node media queue to hand off');
   const source=String(sourceState.node||mediaNode||'');if(!source)throw Error('source media node unavailable');
   // Do not rebuild the native <select> while iOS is dismissing its picker.
   // The selected target is authoritative immediately; polling is suspended until
   // Safari either accepts playback or the transaction rolls back.
   selectedMediaOutput='browser';mediaHandoff=true;browserMedia={active:false,sourceNode:source,index:Number(sourceState.index||0),queue:sourceState.queue.slice(),state:'loading',position:0,duration:0};mediaDismissed=false;event(`MEDIA · MOVE ${source} → ${thisDeviceLabel()}`,true);
   await browserPlayIndex(browserMedia.index);mediaHandoff=false;
   const stop=await fetch('/api/media/control',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action:'stop',node:source})});if(!stop.ok)event('MEDIA WARNING · source stop failed');
   event(`MEDIA · MOVED → ${thisDeviceLabel()}`);renderMedia(browserSnapshot(),true);return
  }
  const nextNode=targetNode(next);if(!nextNode)throw Error('invalid media output');
  if(selectedMediaOutput==='browser'){
   event(`MEDIA · MOVE ${thisDeviceLabel()} → ${nextNode}`,true);
   const r=await fetch('/api/media/move',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({source:browserMedia.sourceNode,target:nextNode,index:browserMedia.index})});const d=await r.json();if(!r.ok||d.error)throw Error(d.error||r.statusText);
   browserAudio.pause();browserAudio.removeAttribute('src');browserAudio.load();browserMedia.active=false;browserMedia.state='stopped';mediaNode=nextNode;selectedMediaOutput=next;nodeMediaState=d;event(`MEDIA · MOVED → ${nextNode}`);renderMedia(d,true);return
  }
  const source=targetNode(previous)||mediaNode;
  if(sourceState?.active&&source&&source!==nextNode){event(`MEDIA · MOVE ${source} → ${nextNode}`,true);const r=await fetch('/api/media/move',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({source,target:nextNode,index:sourceState.index})});const d=await r.json();if(!r.ok||d.error)throw Error(d.error||r.statusText);nodeMediaState=d;event(`MEDIA · MOVED → ${nextNode}`)}
  mediaNode=nextNode;selectedMediaOutput=next;mediaDismissed=false;await pollMedia(true)
 }catch(err){mediaHandoff=false;selectedMediaOutput=previous;if(next==='browser'){browserAudio.pause();browserMedia.active=false;browserMedia.state='stopped'}event('MEDIA MOVE ERROR · '+err.message);renderMedia(previous==='browser'?browserSnapshot():(nodeMediaState||lastMediaState),true)}}
function renderMedia(d,force=false){
 lastMediaState=d||null;if(selectedMediaOutput!=='browser'&&d?.node&&d.node!=='browser')nodeMediaState=d;
 // Native iOS select pickers are tied to the exact DOM element that opened them.
 // Media polling may update state while the picker is open, but must not replace
 // the card/select until Safari finishes the interaction.
 if(mediaPickerActive)return;
 const queue=Array.isArray(d?.queue)?d.queue:[],active=Boolean(d?.active),entry=d?.entry||{};const key=[selectedMediaOutput,d?.state,d?.index,d?.count,entry.artist,entry.album,entry.title].join('|');if(key!==lastMediaKey){if(active)mediaDismissed=false;lastMediaKey=key}
 if(!d?.available||!queue.length||mediaDismissed){mediaPanel.hidden=true;mediaPanel.innerHTML='';return}
 mediaPanel.hidden=false;mediaPanel.innerHTML='';
 const head=document.createElement('div');head.className='media-head';const tag=document.createElement('span');tag.textContent='NOW PLAYING';const state=document.createElement('span');state.className='media-state';state.textContent=String(d.state||'').toUpperCase();head.append(tag,state);
 const title=document.createElement('div');title.className='media-title';title.textContent=entry.title||'Media';const artist=document.createElement('div');artist.className='media-artist';artist.textContent=[entry.artist,entry.album].filter(Boolean).join(' · ');
 const progress=document.createElement('div');progress.className='media-progress';const ratio=(Number(d.duration)>0)?Math.max(0,Math.min(1,Number(d.position||0)/Number(d.duration))):0;const bar=document.createElement('div');bar.className='media-progress-bar';const fill=document.createElement('i');fill.style.width=(ratio*100).toFixed(1)+'%';bar.append(fill);const clock=document.createElement('span');clock.textContent=`${mediaTime(d.position)} / ${mediaTime(d.duration)}`;progress.append(bar,clock);
 const controls=document.createElement('div');controls.className='media-controls';controls.append(mediaButton('◀◀','Previous','prev'),mediaButton(d.state==='paused'?'▶':'❚❚',d.state==='paused'?'Play':'Pause','toggle'),mediaButton('▶▶','Next','next'));
 const outputRow=document.createElement('div');outputRow.className='media-output-row';const outLabel=document.createElement('span');outLabel.textContent='OUT';const outMenu=document.createElement('div');outMenu.className='media-output-menu';
 const choices=[{target:'browser',label:thisDeviceLabel(),available:true},...mediaOutputs.map(row=>({target:nodeTarget(row.node),label:String(row.node||'local'),available:row.available!==false,reason:String(row.reason||row.error||'').trim()}))];
 for(const choice of choices){const b=document.createElement('button');b.type='button';b.className='media-output-choice'+(choice.target===selectedMediaOutput?' selected':'');b.disabled=!choice.available;b.textContent=choice.label+(choice.target===selectedMediaOutput?' ●':'')+(!choice.available&&choice.reason?` · ${choice.reason}`:'');b.onclick=()=>selectMediaOutput(choice.target,b);outMenu.append(b)}
 outputRow.append(outLabel,outMenu);
 const shownOutput=selectedMediaOutput==='browser'?thisDeviceLabel():(targetNode(selectedMediaOutput)||d.node||mediaNode||'local');const meta=document.createElement('div');meta.className='media-meta';meta.textContent=`${shownOutput} · queue ${d.count||queue.length} tracks · ${Number(d.index||0)+1}/${d.count||queue.length}`;
 const actions=document.createElement('div');actions.className='media-actions';const q=document.createElement('button');q.type='button';q.className='media-link';q.textContent=mediaExpanded?'Hide queue':'Queue';q.onclick=()=>{mediaExpanded=!mediaExpanded;renderMedia(selectedMediaOutput==='browser'?browserSnapshot():d,true)};const stop=mediaButton('Stop','Stop playback','stop');stop.classList.add('media-link');const dismiss=document.createElement('button');dismiss.type='button';dismiss.className='media-link';dismiss.textContent='Dismiss';dismiss.onclick=()=>{mediaDismissed=true;mediaPanel.hidden=true};actions.append(q,stop,dismiss);
 mediaPanel.append(head,title,artist,progress,controls,outputRow,meta,actions);if(mediaExpanded){const list=document.createElement('div');list.className='media-queue';queue.forEach((row,i)=>{const b=document.createElement('button');b.type='button';b.className='media-queue-row'+(i===Number(d.index)?' current':'');b.onclick=()=>mediaControl('jump',i);const n=document.createElement('span');n.textContent=String(i+1).padStart(2,'0');const t=document.createElement('span');t.textContent=[row.artist,row.title].filter(Boolean).join(' — ')||'Media';b.append(n,t);list.append(b)});mediaPanel.append(list)}}
async function mediaControl(action,index=null){try{event('MEDIA · '+action.toUpperCase(),true);if(selectedMediaOutput==='browser'){
 if(action==='toggle'){if(browserAudio.paused){await browserAudio.play();browserMedia.active=true;browserMedia.state='playing'}else{browserAudio.pause();browserMedia.state='paused'}}else if(action==='next'){await browserPlayIndex(browserMedia.index+1)}else if(action==='prev'){await browserPlayIndex(browserMedia.index-1)}else if(action==='jump'){await browserPlayIndex(index)}else if(action==='stop'){browserAudio.pause();browserMedia.active=false;browserMedia.state='stopped';mediaPanel.hidden=true}else throw Error('unsupported browser media control');if(browserMedia.active)renderMedia(browserSnapshot(),true);event('MEDIA · '+action.toUpperCase());return}
 const node=targetNode(selectedMediaOutput)||mediaNode;const r=await fetch('/api/media/control',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action,index,node})});const d=await r.json();if(!r.ok||d.error)throw Error(d.error||r.statusText);nodeMediaState=d;mediaDismissed=false;renderMedia(d,true);event('MEDIA · '+action.toUpperCase())}catch(err){event('MEDIA ERROR · '+err.message)}}
async function pollMedia(force=false){if(mediaHandoff)return;if(selectedMediaOutput==='browser'){renderMedia(browserSnapshot(),force);return}const node=targetNode(selectedMediaOutput)||mediaNode;try{const r=await fetch('/api/media?node='+encodeURIComponent(node||''),{cache:'no-store'});if(!r.ok)return;const d=await r.json();nodeMediaState=d;renderMedia(d,force)}catch{}}
browserAudio.addEventListener('timeupdate',()=>{if(selectedMediaOutput==='browser')renderMedia(browserSnapshot())});browserAudio.addEventListener('pause',()=>{if(selectedMediaOutput==='browser'&&browserMedia.active){browserMedia.state='paused';renderMedia(browserSnapshot())}});browserAudio.addEventListener('play',()=>{if(selectedMediaOutput==='browser'){browserMedia.active=true;browserMedia.state='playing';renderMedia(browserSnapshot())}});browserAudio.addEventListener('ended',()=>{if(selectedMediaOutput==='browser'&&browserMedia.index+1<browserMedia.queue.length)browserPlayIndex(browserMedia.index+1).catch(err=>event('MEDIA ERROR · '+err.message));else if(selectedMediaOutput==='browser'){browserMedia.state='stopped';browserMedia.active=false;mediaPanel.hidden=true}});
setInterval(()=>pollMedia(false),1000);pollMediaOutputs().then(()=>pollMedia(true));setInterval(pollMediaOutputs,8000);

let activeDecisionKey='';
function renderDecision(d){
 if(!d){decisionPanel.hidden=true;decisionPanel.innerHTML='';activeDecisionKey='';return}
 const key=String(d.node||'local')+':'+String(d.id||'');
 const left=Math.max(0,Math.ceil((Number(d.expires||0)*1000-Date.now())/1000));
 decisionPanel.hidden=false;decisionPanel.innerHTML='';
 const head=document.createElement('div');head.className='decision-head';
 const who=document.createElement('span');who.textContent=`FABRIC INPUT · ${d.node||d.origin||'local'}`;
 const timer=document.createElement('span');timer.textContent=`${left}s`;head.append(who,timer);
 const q=document.createElement('div');q.className='decision-question';q.textContent=String(d.question||'Decision required');
 const choices=document.createElement('div');choices.className='decision-choices';
 for(const choice of (d.choices||[])){const b=document.createElement('button');b.type='button';b.className='decision-choice';b.textContent=String(choice.label||choice.value);b.onclick=()=>answerDecision(d,choice.value);choices.append(b)}
 const meta=document.createElement('div');meta.className='decision-meta';
 const fallback=String(d.fallback||'defer');meta.textContent=`${d.profile||'workspace'} · ${Math.round(Number(d.confidence||0)*100)}% · timeout: ${fallback}`;
 decisionPanel.append(head,q,choices,meta);
 if(key!==activeDecisionKey){event('FABRIC INPUT REQUEST');activeDecisionKey=key}
}
async function answerDecision(d,selected){
 try{const r=await fetch('/api/fabric/decisions/answer',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({node:d.node,id:d.id,selected})});const out=await r.json();if(!r.ok||out.error)throw Error(out.error||r.statusText);event(`FABRIC INPUT · ${selected}`);activeDecisionKey='';await pollDecisions();input.focus()}catch(err){event('DECISION ERROR · '+err.message)}
}
async function pollDecisions(){
 try{const r=await fetch('/api/fabric/decisions',{cache:'no-store'});if(!r.ok)return;const d=await r.json();const rows=Array.isArray(d.decisions)?d.decisions:[];renderDecision(rows[0]||null)}catch{}
}
setInterval(pollDecisions,750);pollDecisions();

let lastFabricLight='';
async function pollFabricLight(){
 try{const r=await fetch('/api/fabric/lights',{cache:'no-store'});if(!r.ok)return;const d=await r.json();const light=d.light||null;const color=String(light?.color||'off');const key=(light?.show_id||light?.id||'')+':'+color;
  const css={red:'#7b1717',green:'#176b35',blue:'#173d7b',white:'#d8e4dc',off:'transparent'}[color]||'transparent';
  fabricLight.style.background=css;fabricLight.style.opacity=color==='off'?'0':'0.82';
  if(light&&key!==lastFabricLight){event(`FABRIC ${String(light.pattern||'LIGHT').toUpperCase()} · ${color.toUpperCase()}`);lastFabricLight=key}
  if(!light){fabricLight.style.opacity='0';lastFabricLight=''}
 }catch{}
}
setInterval(pollFabricLight,400);pollFabricLight();

input.addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();form.requestSubmit()}});
