(function(){
  const $=id=>document.getElementById(id);let busy=false;
  function text(tag,value,cls=''){const el=document.createElement(tag);el.textContent=String(value??'Unknown');el.className=cls;return el}
  function field(list,label,value){list.append(text('dt',label),text('dd',value))}
  function stamp(value){return value?new Date(Number(value)*1000).toLocaleString():'Unknown'}
  async function json(path,timeout){const ctl=new AbortController();const timer=setTimeout(()=>ctl.abort(),timeout);try{const response=await fetch(path,{cache:'no-store',signal:ctl.signal});if(!response.ok)throw Error(response.status===403?'Authorize this browser in Signal or Albert first.':'Host returned '+response.status);return await response.json()}finally{clearTimeout(timer)}}
  function renderNodes(snapshot){
    const target=$('nodes');target.replaceChildren();
    const own=snapshot.self||{};
    const rows=[{...own,local:true},...(snapshot.peers||[])];
    if(!rows.some(row=>row.name||row.identity?.name)){target.append(text('p','No node information returned.','unknown'));return}
    for(const row of rows){
      const node=row.node||row;const name=node.identity?.name||row.name||'This computer';
      const available=row.local||(!row.node_error&&Number(row.node_seen_at)>Date.now()/1000-45);
      const card=document.createElement('article');card.append(text('h2',name));
      card.append(text('p',row.local?'This browser’s host':available?'Recently reachable':row.node_error?'Unreachable at last check':'Reachability unknown',available?'good':'unknown'));
      const dl=document.createElement('dl');field(dl,'Last seen',row.local?'Now':stamp(row.node_seen_at));
      const models=node.inference?.models||[];field(dl,'Inference',models.length?models.map(x=>x.name||x).join(', '):'No advertised models');
      const active=node.supervisor?.active;field(dl,'Activity',active?.detail||active?.phase||'No current activity reported');card.append(dl);
      target.append(card);
    }
  }
  function renderCare(report){
    const target=$('care');target.replaceChildren();
    $('careStatus').textContent='Receipts checked '+new Date().toLocaleTimeString()+' · '+(report.releases_match?'Installed bundles agree':'Installed bundles differ or a node could not be checked');
    for(const row of report.nodes||[]){
      const card=document.createElement('article');card.append(text('h2',row.node));const dl=document.createElement('dl');
      const release=row.release||{},update=row.update||{},backup=row.backup;
      field(dl,'Installed',release.commit?String(release.commit).slice(0,7):'Unknown');
      field(dl,'Updater',update.state||'No current receipt');
      field(dl,'Backup',!backup?'Unknown':backup.verified_recently?'Restore-tested within 24 hours':backup.configured?'No recent verified backup':'Setup needed');
      field(dl,'Verified',stamp(backup?.verified_at));
      if(backup?.configured)field(dl,'Backup storage',backup.connected?'Connected':'Disconnected or unavailable');
      card.append(dl);
      card.append(text('p',row.errors?.length?'Some checks unavailable':backup?.verified_recently?'Essential backup verified':'Needs attention',row.errors?.length?'unknown':backup?.verified_recently?'good':'warn'));
      if(row.errors?.length){const details=document.createElement('details');details.append(text('summary','Check details'),text('pre',row.errors.map(x=>x.check+': '+x.error).join('\n')));card.append(details)}
      target.append(card);
    }
  }
  async function refresh(){
    if(busy)return;busy=true;$('refresh').disabled=true;
    $('status').textContent='Refreshing node advertisements…';$('careStatus').textContent='Checking receipts; unreachable peers may take longer…';
    await Promise.allSettled([
      json('/api/fabric',15000).then(data=>{renderNodes(data.nodes||{});$('status').textContent='Node advertisements checked '+new Date().toLocaleTimeString()+' · cached peer advertisements may be older.'}).catch(error=>{$('status').textContent='Node check failed: '+error.message+' Previous information may be stale.'}),
      json('/api/fabric/care',95000).then(renderCare).catch(error=>{$('careStatus').textContent='Backup/update check failed: '+error.message+' Previous receipts may be stale.'})
    ]);
    busy=false;$('refresh').disabled=false;
  }
  $('refresh').onclick=refresh;refresh();
  // Care traverses trusted peers; avoid turning a quiet dashboard into polling load.
  setInterval(()=>{if(!document.hidden)refresh()},60000);
})();
