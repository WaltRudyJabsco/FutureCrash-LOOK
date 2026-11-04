/* Shared Signal/Albert observatory. Animation is decoration; numbers are receipts. */
(function(){
  const $=id=>document.getElementById(id),POLL_MS=8000,CARE_MS=60000,MAX_EVENTS=160;
  let busy=false,careBusy=false,paused=false,last=0,events=new Map();
  const text=(tag,value,cls='')=>{const el=document.createElement(tag);el.textContent=String(value??'Unknown');el.className=cls;return el};
  const stamp=value=>value?new Date(Number(value)*1000).toLocaleString():'Unknown';
  async function json(path,timeout){const ctl=new AbortController(),timer=setTimeout(()=>ctl.abort(),timeout);try{const r=await fetch(path,{cache:'no-store',signal:ctl.signal});if(!r.ok)throw Error(r.status===403?'Authorize this browser in Signal or Albert first.':'Host returned '+r.status);return await r.json()}finally{clearTimeout(timer)}}
  function svg(tag,attrs){const el=document.createElementNS('http://www.w3.org/2000/svg',tag);for(const [k,v] of Object.entries(attrs))el.setAttribute(k,v);return el}
  function map(nodes){
    const root=svg('svg',{viewBox:'0 0 640 350',role:'img','aria-label':'Host and trusted Fabric peers'}),cx=320,cy=170;
    root.append(svg('circle',{cx,cy,r:115,class:'ring'}),svg('circle',{cx,cy,r:65,class:'ring'}));
    const peers=Math.max(1,nodes.length-1);
    nodes.forEach((node,i)=>{
      const angle=(i-1)/peers*Math.PI*2-Math.PI/2,x=i?cx+205*Math.cos(angle):cx,y=i?cy+115*Math.sin(angle):cy;
      if(i)root.append(svg('line',{x1:cx,y1:cy,x2:x,y2:y}));
      const g=svg('g',{class:node.reachable?'online':'offline'});
      g.append(svg('circle',{cx:x,cy:y,r:20,class:'orbit'}),svg('circle',{cx:x,cy:y,r:16,class:'node'}));
      const name=svg('text',{x,y:y+37,'text-anchor':'middle'});name.textContent=node.name.length>25?node.name.slice(0,23)+'…':node.name;
      const label=svg('text',{x,y:y+52,'text-anchor':'middle',class:'sub'});label.textContent=node.reachable?(node.activity?.phase||'idle').toUpperCase():'UNKNOWN';g.append(name,label);root.append(g);
    });$('map').replaceChildren(root);
  }
  function nodeCards(nodes){
    const expanded=new Set([...$('nodes').querySelectorAll('article')].filter(card=>card.querySelector('details')?.open).map(card=>card.dataset.node));
    const cards=nodes.map(node=>{
      const card=text('article','','node-card'),head=text('div','','node-top'),title=text('div','');title.append(text('h2',node.name),text('p',[node.platform,node.architecture,node.local?'THIS HOST':'PEER'].filter(Boolean).join(' · '),'label'));
      card.dataset.node=node.name;head.append(title,text('span',node.reachable?'REACHABLE':'UNKNOWN','badge'+(node.reachable?'':' unknown')));card.append(head);
      if(!node.reachable){card.append(text('p','Telemetry unavailable. This peer may be offline or need an update.','warn'),text('p','Last advertisement: '+stamp(node.observed_at),'muted'));return card}
      card.append(text('p','Supervisor · '+(node.activity?.phase||'idle'),node.activity?.phase&&node.activity.phase!=='idle'?'good':'muted'));
      const services=text('div','','services');for(const [name,value] of Object.entries(node.services||{})){const state=value.state||'unknown';services.append(text('span',name+' · '+state,'service '+state.replace(/[^a-z]/g,'')))}card.append(services);if(node.runtime_ok===false)card.append(text('p','Runtime health needs attention','warn'));
      const models=text('div','','models'),resident=(node.models||[]).filter(m=>m.resident);models.append(text('div',(node.models||[]).length+' MODELS AVAILABLE · '+resident.length+' RESIDENT','label'));
      for(const model of resident)models.append(text('p','● '+model.name,'resident'));
      if(!resident.length)models.append(text('p','No models currently resident','muted'));
      const details=document.createElement('details');details.open=expanded.has(node.name);details.append(text('summary','Model inventory'));for(const model of node.models||[])details.append(text('p',model.name));models.append(details);card.append(models);
      card.append(text('p','Installed '+(node.release?.commit?.slice(0,7)||'unknown')+' · '+(node.release?.state||'no update receipt'),'muted'));return card;
    });$('nodes').replaceChildren(...cards);
  }
  function renderEvents(){
    const selected=$('filter').value,rows=[...events.values()].filter(e=>!selected||e.source===selected).sort((a,b)=>b.ts-a.ts);
    const view=rows.slice(0,60).map(e=>{const row=text('div','','event');row.dataset.error=String(/fail|error/i.test(e.type+' '+e.phase));const time=text('time',new Date(e.ts*1000).toLocaleTimeString([],{hour:'2-digit',minute:'2-digit',second:'2-digit',hour12:false}));time.title=stamp(e.ts);const content=text('div','');content.append(text('strong',e.source),text('span',[e.type,e.phase].filter(Boolean).join(' / '),'kind'));row.append(time,content);return row});
    $('events').replaceChildren(...(view.length?view:[text('p','No recent events observed for this selection. Quiet is a valid state.','empty')]));
    $('eventCount').textContent=rows.length+' OBSERVED';
    $('ticker').textContent=rows.slice(0,8).map(e=>new Date(e.ts*1000).toLocaleTimeString()+'  '+e.source+' · '+e.type+' / '+(e.phase||'')).join('     ／     ')||'No recent events observed';
  }
  function render(data){
    const nodes=data.nodes||[],reachable=nodes.filter(n=>n.reachable),selected=$('filter').value;
    $('nodeCount').textContent=reachable.length+' / '+nodes.length;
    $('serviceCount').textContent=reachable.reduce((n,row)=>n+Object.values(row.services||{}).filter(s=>['running','active'].includes(s.state)).length,0);
    $('modelCount').textContent=reachable.reduce((n,row)=>n+(row.models||[]).filter(m=>m.resident).length,0);
    $('activeCount').textContent=reachable.filter(n=>n.activity?.phase&&n.activity.phase!=='idle').length;
    $('host').textContent='HOST · '+data.host;map(nodes);nodeCards(nodes);
    const options=[text('option','All computers')];options[0].value='';for(const node of nodes){const option=text('option',node.name);option.value=node.name;options.push(option)}$('filter').replaceChildren(...options);$('filter').value=nodes.some(n=>n.name===selected)?selected:'';
    for(const event of data.events||[])events.set(event.id,event);
    events=new Map([...events.values()].sort((a,b)=>a.ts-b.ts).slice(-MAX_EVENTS).map(e=>[e.id,e]));renderEvents();
    last=Number(data.observed_at)*1000;$('connection').textContent='CONNECTED · '+reachable.length+' NODES';
    $('status').textContent='Observed '+new Date(last).toLocaleTimeString()+(data.omitted_peers?' · '+data.omitted_peers+' peers beyond display limit':'');$('status').className='muted';
  }
  async function refresh(){if(busy||paused||document.hidden)return;busy=true;$('refresh').disabled=true;try{const data=await json('/api/fabric/dashboard',15000);if(!paused)render(data)}catch(error){$('connection').textContent='CONNECTION UNAVAILABLE';$('status').textContent=error.message+(last?' Last snapshot: '+new Date(last).toLocaleTimeString():'');$('status').className='error'}finally{busy=false;$('refresh').disabled=false}}
  function renderCare(report){
    $('careStatus').textContent='Checked '+new Date().toLocaleTimeString()+' · '+(report.releases_match?'Installed bundles agree':'Bundles differ or checks incomplete');
    $('care').replaceChildren(...(report.nodes||[]).map(row=>{const card=text('article','','receipt');card.append(text('h2',row.node));const dl=text('dl',''),field=(name,value)=>dl.append(text('dt',name),text('dd',value));field('Installed',row.release?.commit?.slice(0,7)||'Unknown');field('Updater',row.update?.state||'Unknown');field('Backup',!row.backup?'Unknown':row.backup.verified_recently?'Restore-tested within 24 hours':row.backup.configured?'No recent verified backup':'Setup needed');field('Verified',stamp(row.backup?.verified_at));card.append(dl);if(row.errors?.length)card.append(text('p','Some checks unavailable','warn'));return card}));
  }
  async function care(){if(careBusy||paused||document.hidden)return;careBusy=true;try{const data=await json('/api/fabric/care',95000);if(!paused)renderCare(data)}catch(e){$('careStatus').textContent='Receipts unavailable: '+e.message+' Previous receipts may be stale.'}finally{careBusy=false}}
  $('refresh').onclick=()=>{refresh();care()};$('filter').onchange=renderEvents;
  $('pause').onclick=()=>{paused=!paused;document.body.classList.toggle('paused',paused);$('pause').textContent=paused?'Resume live':'Pause live';$('pause').setAttribute('aria-pressed',paused);$('connection').textContent=paused?'LIVE UPDATES PAUSED':'Reconnecting';if(!paused){refresh();care()}};
  $('theater').onclick=()=>{const on=document.body.classList.toggle('theater');$('theater').setAttribute('aria-pressed',on);$('theater').textContent=on?'Overview':'Focus'};
  $('fullscreen').onclick=async()=>{try{if(document.fullscreenElement)await document.exitFullscreen();else if(document.documentElement.requestFullscreen)await document.documentElement.requestFullscreen();else{$('theater').click();$('status').textContent='Full screen unavailable in this browser; focus view enabled.'}}catch(e){$('status').textContent='Full screen unavailable. Use Focus to simplify the view.'}};
  document.addEventListener('fullscreenchange',()=>{$('fullscreen').textContent=document.fullscreenElement?'Exit full screen':'Full screen'});
  document.addEventListener('visibilitychange',()=>{if(!document.hidden){refresh();care()}});
  setInterval(refresh,POLL_MS);setInterval(care,CARE_MS);
  setInterval(()=>{if(last&&!paused&&Date.now()-last>30000)$('connection').textContent='STALE · LAST SNAPSHOT '+Math.floor((Date.now()-last)/1000)+'s AGO'},1000);
  refresh();care();
})();
