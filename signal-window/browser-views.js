/* Shared by Signal and Albert: browser-local views, never compute-worker windows. */
(function(root){
  const IMAGE_WAIT_MS=15*60*1000,CHAT_WAIT_MS=185000;
  function imageRequest(text){
    const value=String(text||'');
    return ((/\b(generate|draw|render|paint|illustrate|create|make)\b/i.test(value)&&
      /\b(image|picture|photo|photograph|illustration|artwork|drawing|painting|portrait|poster|logo|sketch|wallpaper)\b/i.test(value))||
      /^(?:please\s+)?(?:draw|paint|illustrate)\s+/i.test(value)||
      (/^(?:please\s+)?generate\s+/i.test(value)&&!/\b(code|script|report|summary|password|key|backup|playlist|note)\b/i.test(value)))&&
      !/\b(?:don't|do not|never)\s+(?:generate|draw|render|paint|create|make)\b/i.test(value);
  }
  function imageArtifacts(payload){
    const found=[];const seen=new Set();
    function add(item){
      const type=String(item?.type||item?.mime||'');
      if(type!=='image'&&!type.startsWith('image/'))return;
      try{
        const url=new URL(item.url||item.src,root.location.href);
        if(!/^https?:$/.test(url.protocol)||url.origin!==root.location.origin||
           !/^\/(?:api\/present\/|v1\/artifacts\/|api\/artifact\?)/.test(url.pathname+url.search)||seen.has(url.href))return;
        seen.add(url.href);found.push({url:url.href,name:String(item.name||item.title||'Generated image')});
      }catch{}
    }
    function visit(value){
      if(!value||typeof value!=='object')return;
      if(Array.isArray(value)){value.forEach(visit);return}
      add(value);(value.artifacts||[]).forEach(add);
      if(value.items)visit(value.items);if(value.result)visit(value.result);if(value.fold)visit(value.fold);
    }
    visit(payload);return found;
  }
  function beginImage(text){
    const wanted=imageRequest(text);let tab=null;
    // Reserve during the submit gesture; opening after a long generation is
    // otherwise blocked by Safari and other browsers' transient activation rules.
    if(wanted){try{tab=root.open('about:blank','_blank');if(tab){tab.opener=null;tab.document.title='Generating image';tab.document.body.textContent='Generating your image… This tab will display it when it is ready.'}}catch{}}
    return {
      wanted,
      // Scope long waits to image work; ordinary requests keep their own budget.
      timeoutMs:wanted?IMAGE_WAIT_MS:CHAT_WAIT_MS,
      finish(payload){
        const images=imageArtifacts(payload);
        if(!wanted)return {images,opened:false};
        if(!images.length){const error='No image file was received. Generation is not confirmed; check the response in Signal or Albert for the worker error.';this.fail(error);return {images,opened:false,error}}
        try{if(tab&&!tab.closed){tab.location.replace(images[0].url);tab=null;return {images,opened:true}}}catch{}
        return {images,opened:false};
      },
      fail(message){try{if(tab&&!tab.closed){tab.document.title='Image result not confirmed';tab.document.body.textContent=String(message||'No image result was confirmed. The worker may still be running. Return to Signal or Albert for details.')}}catch{}},
      cancel(){try{if(tab&&!tab.closed)tab.close()}catch{}tab=null}
    };
  }
  function fabricCommand(text){return /^(?:\/fabric|(?:please\s+)?(?:show|open)(?:\s+(?:me|our|the))?\s+fabric(?:\s+(?:dash|dashboard|status))?)[.!?]?$/i.test(String(text||'').trim())}
  function openFabric(){
    const url=new URL('/fabric.html',root.location.href).href;
    try{root.open(url,'_blank','noopener')}catch{}
    return url;
  }
  function booksCommand(text){
    const value=String(text||'').trim().replace(/[.!?]+$/,'');
    if (/^\/books$/i.test(value))return {query:'',resume:false};
    if (/^(?:please\s+)?continue (?:reading|listening)(?:\s+please)?$/i.test(value))return {query:'',resume:true};
    if(/^(?:please\s+)?read\s+(?:(?:my|our|the)\s+)?(?:notes?|files?|articles?|webpages?|messages?|clipboard)\b/i.test(value))return null;
    if(/^continue\s+(?:with|that|this|your|writing|from|working|on)\b/i.test(value))return null;
    const match=value.match(/^(?:please\s+)?(?:read|continue(?: reading)?|listen to)\s+(.+?)(?:\s+please)?$/i);
    return match?{query:match[1],resume:true}:null;
  }
  function openBooks(command){
    const url=new URL('/books',root.location.href);
    if(command.query)url.searchParams.set('query',command.query);
    if(command.resume)url.searchParams.set('resume','1');
    try{root.open(url.href,'_blank','noopener')}catch{}
    return url.href;
  }
  root.FabricBrowserViews={beginImage,imageArtifacts,imageRequest,fabricCommand,openFabric,booksCommand,openBooks};
})(globalThis);


// Books uses the same authorized host gateway in Signal and Albert.
(async function(){
  if(typeof document==='undefined'||!document.getElementById?.('books-app'))return;
  const $=id=>document.getElementById(id),audio=$('audio');
  let catalog=[],book=null,model=null,chapter=0,paragraph=0,generation=0,lastSave=0,saving=Promise.resolve();
  function status(text){$('status').textContent=text}
  async function api(route='',payload){
    const response=await fetch('/api/books'+route,payload?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)}:{cache:'no-store'});
    const value=await response.json();if(!response.ok||value.error)throw Error(value.error||'Books request failed');return value;
  }
  function params(extra={}){return new URLSearchParams({target:book.node||'local',id:book.id,...extra})}
  function save(finished=false){
    if(!book||!model)return;
    const route='/progress?'+params(),id=book.id,fields={chapter,paragraph,offset:Number.isFinite(audio.currentTime)?audio.currentTime:0,finished};
    book.reading={...fields,updated:Date.now()/1000};
    saving=saving.catch(()=>{}).then(()=>api(route,{id,fields})).catch(error=>status('Progress not saved: '+error.message));
  }
  async function load(c,p,autoplay=false,resumeOffset=0){
    const mine=++generation;audio.pause();audio.removeAttribute('src');audio.load();
    status('Preparing your reading position…');
    const value=await api('/read?'+params(c===undefined?{}:{chapter:c,paragraph:p}));
    if(mine!==generation)return;
    model=value;chapter=value.chapter;paragraph=value.paragraph;
    $('reader').hidden=false;$('title').textContent=book.title;$('passage').textContent=value.text;
    $('where').textContent=`${value.chapters[chapter].title} · paragraph ${paragraph+1}/${value.chapters[chapter].paragraphs}`;
    $('chapters').replaceChildren(...value.chapters.map((row,i)=>{const o=document.createElement('option');o.value=i;o.textContent=row.title;return o}));$('chapters').value=chapter;
    $('cover').hidden=false;$('cover').src='/api/books/cover?'+params();$('cover').onerror=()=>{$('cover').hidden=true};
    audio.src='/api/books/audio?'+params({chapter,paragraph});
    const offset=c===undefined?(value.reading.offset||0):resumeOffset;
    audio.onloadedmetadata=()=>{if(mine===generation&&offset&&offset<audio.duration)audio.currentTime=offset};
    audio.onerror=()=>status('Narration unavailable. Check that the book owner is reachable and has a speech voice and ffmpeg installed.');
    status('Ready. Press Play to prepare narration and listen on this device.');
    if(autoplay){status('Preparing narration…');await audio.play().catch(()=>status('Tap Play to continue listening.'))}
  }
  async function open(row){if(book)save();book=row;model=null;await load()}
  async function move(delta,autoplay=false){
    if(!model)return;save();let c=chapter,p=paragraph+delta;
    if(p>=model.chapters[c].paragraphs){if(c+1>=model.chapters.length){save(true);status('Book finished.');return}c++;p=0}
    if(p<0){if(c===0)return;c--;p=model.chapters[c].paragraphs-1}
    await load(c,p,autoplay);save();
  }
  function button(label,click){const b=document.createElement('button');b.textContent=label;b.onclick=()=>Promise.resolve().then(click).catch(e=>status(e.message));return b}
  function show(rows,discover=false){
    $('items').replaceChildren(...rows.map(row=>button(row.title+(row.author?' — '+row.author:''),async()=>{
      if(row.kind==='subject')return discoverMode('subject',row.subject);
      if(!discover)return open(row);
      if(!confirm('Download '+row.title+' to this Fabric host’s books library?'))return;
      status('Downloading book…');const value=await api('/fetch',{url:row.url});await shelf();status('Added to your shelf: '+value.book.title);
    })));
    if(discover)document.querySelectorAll('#items button').forEach((b,i)=>{
      const id=rows[i].url?.match(/\/ebooks\/(\d+)\.opds/);if(!id)return;
      const img=document.createElement('img');img.alt='';img.loading='lazy';img.src='/api/books/discovery-cover?id='+id[1];img.style.cssText='width:45px;max-height:65px;object-fit:contain;vertical-align:middle;margin-right:12px';img.onerror=()=>img.remove();b.prepend(img);
    });
    if(!rows.length)status('No books found.');
  }
  async function shelf(){status('Loading Fabric shelf…');const value=await api();catalog=value.entries||[];show(catalog);status(value.errors?.length?'Some book owners are unavailable.':'Choose a book or continue reading.')}
  async function discoverMode(mode,subject=''){status('Browsing Project Gutenberg…');const value=await api('/discover?'+new URLSearchParams({mode,subject}));show(value.entries||[],true);status('Project Gutenberg · select a title to download. Surprise me samples the popular list.')}
  async function resume(query=''){
    await shelf();const terms=query.toLocaleLowerCase().split(/\s+/).filter(Boolean);
    const rows=catalog.filter(row=>(query||!row.reading?.finished)&&terms.every(t=>(row.title+' '+row.author).toLocaleLowerCase().includes(t))).sort((a,b)=>(b.reading?.updated||0)-(a.reading?.updated||0));
    if(!rows.length){status('No matching book on your Fabric shelf. Try Discover to add it.');return}
    if(query&&new Set(rows.map(r=>r.id)).size>1){show(rows);status('Choose the book you meant.');return}
    if(!query&&!rows[0].reading?.updated){show(rows);status('Choose a book to begin reading.');return}
    await open(rows[0]);
  }
  $('shelf').onclick=()=>shelf().catch(e=>status(e.message));$('continue').onclick=()=>resume().catch(e=>status(e.message));
  document.querySelectorAll('[data-mode]').forEach(b=>b.onclick=()=>discoverMode(b.dataset.mode).catch(e=>status(e.message)));
  $('search').onsubmit=e=>{e.preventDefault();resume($('query').value).catch(e=>status(e.message))};
  $('previous').onclick=()=>move(-1).catch(e=>status(e.message));$('next').onclick=()=>move(1).catch(e=>status(e.message));
  $('retry').onclick=()=>load(chapter,paragraph,true,audio.currentTime||0).catch(e=>status(e.message));
  $('chapters').onchange=()=>load(Number($('chapters').value),0).then(()=>save()).catch(e=>status(e.message));
  audio.onplay=()=>{status('Preparing / playing narration…');save()};audio.onplaying=()=>status('Reading on this device.');
  audio.onpause=()=>save();audio.ontimeupdate=()=>{if(Date.now()-lastSave>5000){lastSave=Date.now();save()}};
  audio.onended=()=>move(1,true).catch(e=>status(e.message));
  window.addEventListener('pagehide',()=>{if(book&&model)fetch('/api/books/progress?'+params(),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:book.id,fields:{chapter,paragraph,offset:audio.currentTime||0}}),keepalive:true}).catch(()=>{})});
  try{await shelf();const q=new URLSearchParams(location.search);if(q.has('resume')||q.has('query'))await resume(q.get('query')||'')}catch(e){status(e.message)}
})();
