const N=256;
const main=document.querySelector('main'),A=document.querySelector('#ambient'),a=A.getContext('2d'),C=document.querySelector('#signal'),c=C.getContext('2d');
const log=document.querySelector('#log'),form=document.querySelector('#form'),input=document.querySelector('#input'),drops=document.querySelector('#drops'),statusEl=document.querySelector('#status'),activity=document.querySelector('#activity'),activityText=document.querySelector('#activityText');
a.imageSmoothingEnabled=c.imageSmoothingEnabled=false;
let files=[],energy=.22,mood='quiet',particles=[],artQuietUntil=0;
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
function chips(){drops.innerHTML='';for(const f of files){const x=document.createElement('span');x.className='chip';x.textContent=f.path||f.name;drops.append(x)}}
async function fileObj(file,path=file.name){let content='';if(file.size<1_000_000){try{content=await file.text()}catch{content='[binary/unreadable]'}}else content=`[file omitted: ${file.size} bytes]`;return{name:file.name,path,size:file.size,type:file.type,content}}
async function walk(entry,prefix=''){if(entry.isFile)return new Promise(r=>entry.file(async f=>r([await fileObj(f,prefix+f.name)])));if(entry.isDirectory){const rd=entry.createReader(),out=[];while(true){const b=await new Promise(r=>rd.readEntries(r));if(!b.length)break;for(const e of b)out.push(...await walk(e,prefix+entry.name+'/'))}return out}return[]}
addEventListener('dragover',e=>{e.preventDefault();document.body.classList.add('drag')});addEventListener('dragleave',()=>document.body.classList.remove('drag'));addEventListener('drop',async e=>{e.preventDefault();document.body.classList.remove('drag');const out=[];for(const item of e.dataTransfer.items||[]){const en=item.webkitGetAsEntry?.();if(en)out.push(...await walk(en));else{const f=item.getAsFile?.();if(f)out.push(await fileObj(f))}}files=out.slice(0,20);chips();input.focus()});
form.addEventListener('submit',async e=>{e.preventDefault();const text=input.value.trim();if(!text&&!files.length)return;line('user','› '+(text||`[${files.length} dropped item${files.length===1?'':'s'}]`));input.value='';const sent=files;files=[];chips();
 if(/^\/(help|lk)$/i.test(text)){line('assistant','Signal commands: /help · /clear · /status · /gallery. Everything else goes to LO.');return}
 if(/^\/clear$/i.test(text)){log.innerHTML='';c.clearRect(0,0,N,N);art.born=0;event('CLEARED');return}
 if(/^\/status$/i.test(text)){status();line('system',statusEl.title||statusEl.textContent);return}
 if(/^\/gallery$/i.test(text)){try{const d=await(await fetch('/api/status')).json();line('system','Gallery: '+(d.gallery||'disabled'))}catch{line('system','Gallery unavailable')}return}
 energy=.65;event('LO REQUEST',true);
 // Visual expression is independent work: start it immediately instead of waiting behind LO.
 const visualPromise=text?fetch('/api/visual',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text})}).then(r=>r.json()).catch(()=>null):Promise.resolve(null);
 try{const r=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text,files:sent,visual:false})});const d=await r.json();if(!r.ok||d.error)throw Error(d.error||r.statusText);if(d.text)line('assistant',d.text);if(Array.isArray(d.lo_events) && d.lo_events.length){
   for(const e of d.lo_events){
     const name=String(e.event||'').replaceAll('_',' ');
     if(!name)continue;
     let detail=e.model||e.tool||e.tokens||e.message||'';
     event(`LO ${name}${detail?' · '+detail:''}`);
   }
 } else event('LO RESPONSE');
 if(Array.isArray(d.artifacts))for(const x of d.artifacts){const a=document.createElement('a');a.href=x.url;a.target='_blank';a.rel='noopener';a.textContent='↗ '+x.name;a.className='artifact';log.append(a);event('ARTIFACT READY · '+x.name)}
 const vd=await visualPromise; const vk=vd?.visual?.kind;
 if(vk==='draw'){event(vd.visual.attempts>1?'SIGNAL REPAIRED':'SIGNAL RESPONSE');draw(vd.signal)}
 else if(vk==='nochange')event('SIGNAL NO CHANGE');
 else if(vk==='error')event('SIGNAL ERROR · '+(vd.visual.error||'UNKNOWN'));
 event('READY');energy=Math.max(.25,energy*.65)}
 catch(err){event('ERROR · '+err.message);line('error','! '+err.message);energy=.15}});
input.addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();form.requestSubmit()}});
