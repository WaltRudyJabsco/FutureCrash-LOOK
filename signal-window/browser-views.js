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
  function createBookAhead({read,audio,createURL=blob=>URL.createObjectURL(blob),revokeURL=url=>URL.revokeObjectURL(url)}){
    let entry=null;
    function clear(){
      const old=entry;entry=null;if(!old)return;
      old.controller.abort();if(old.url)revokeURL(old.url);
    }
    return {
      clear,
      prepare(key,readRoute,audioRoute){
        if(entry?.key===key)return entry.promise;
        clear();const current={key,controller:new AbortController(),url:''};entry=current;
        current.promise=Promise.all([read(readRoute,current.controller.signal),audio(audioRoute,current.controller.signal)]).then(([value,blob])=>{
          if(current.controller.signal.aborted)return null;
          current.url=createURL(blob);return {value,url:current.url};
        }).catch(()=>{if(entry===current)clear();return null});
        return current.promise;
      },
      take(key){
        if(!entry||entry.key!==key){clear();return null}
        // Keep an unfinished handoff cancelable if the reader seeks again.
        const current=entry;
        return current.promise.then(result=>{if(entry===current)entry=null;return result});
      }
    };
  }
  function bookPosition(chapters,chapter,paragraph,delta=1){
    let c=chapter,p=paragraph+delta;
    if(p>=chapters[c].paragraphs){c++;p=0}
    if(p<0){c--;if(c>=0)p=chapters[c].paragraphs-1}
    return c<0||c>=chapters.length?null:{chapter:c,paragraph:p};
  }
  function booksCommand(text){
    const value=String(text||'').trim().replace(/[.!?]+$/,'');
    if (/^\/(?:books|reader|mercury-reader)$/i.test(value)||/^(?:open\s+)?mercury reader$/i.test(value))return {query:'',resume:false};
    if (/^(?:please\s+)?continue (?:reading|listening)(?:\s+please)?$/i.test(value))return {query:'',resume:true};
    if(/^(?:please\s+)?read\s+(?:(?:my|our|the)\s+)?(?:notes?|files?|articles?|webpages?|messages?|clipboard)\b/i.test(value))return null;
    if(/^continue\s+(?:with|that|this|your|writing|from|working|on)\b/i.test(value))return null;
    const match=value.match(/^(?:please\s+)?(?:read|continue(?: reading)?|listen to)\s+(.+?)(?:\s+please)?$/i);
    return match?{query:match[1],resume:true}:null;
  }
  function openBooks(command){
    const url=new URL('/reader',root.location.href);
    if(command.query)url.searchParams.set('query',command.query);
    if(command.resume)url.searchParams.set('resume','1');
    try{root.open(url.href,'_blank','noopener')}catch{}
    return url.href;
  }
  root.FabricBrowserViews={beginImage,imageArtifacts,imageRequest,fabricCommand,openFabric,booksCommand,openBooks,createBookAhead,bookPosition};
})(globalThis);


// Books uses the same authorized host gateway in Signal and Albert.
(async function(){
  if(typeof document==='undefined'||!document.getElementById?.('books-app'))return;
  const $=id=>document.getElementById(id),audio=$('audio');
  let libraryGeneration=0,shelfQuery='',discovery=null,sortOrder='title';
  try{sortOrder=localStorage.getItem('look-books-shelf-sort')||'title'}catch{}
  if(!['title','author','opened','added'].includes(sortOrder))sortOrder='title';
  let catalog=[],book=null,model=null,chapter=0,paragraph=0,generation=0,lastSave=0,saving=Promise.resolve();
  let activeAudioURL='',playbackIntent=false,switchingAudio=false,requestedPosition=null;
  const MAX_AHEAD_AUDIO_BYTES=8*1024*1024;
  const ahead=FabricBrowserViews.createBookAhead({
    read:(route,signal)=>api(route,undefined,signal),
    audio:async(route,signal)=>{
      const response=await fetch(route,{signal,cache:'no-store'});
      if(!response.ok||Number(response.headers.get('Content-Length'))>MAX_AHEAD_AUDIO_BYTES)throw Error('Next narration unavailable');
      const blob=await response.blob();if(blob.size>MAX_AHEAD_AUDIO_BYTES)throw Error('Next narration too large');return blob;
    }
  });
  function releaseAudio(){if(activeAudioURL)URL.revokeObjectURL(activeAudioURL);activeAudioURL=''}
  function narrationRoute(c,p){return '/api/books/audio?'+params({chapter:c,paragraph:p,pauses,...((selectedVoice||defaultVoice)?{voice:selectedVoice||defaultVoice}:{})})}
  function prepareNext(){
    if(!book||!model||audio.paused||audio.ended)return;
    const next=FabricBrowserViews.bookPosition(model.chapters,chapter,paragraph);
    if(!next){ahead.clear();return}
    const route=narrationRoute(next.chapter,next.paragraph);
    ahead.prepare(route,'/read?'+params({...next,content:next.chapter===chapter?'0':'1'}),route);
  }
  let content=null,follow=true,fontSize=21,theme='paper',speed=1,selectedVoice='',defaultVoice='',voiceByOwner={},pauses='natural';
  try{const prefs=JSON.parse(localStorage.getItem('look-books-appearance')||'{}');
    fontSize=Math.max(16,Math.min(32,Number(prefs.fontSize)||21));theme=prefs.theme==='dark'?'dark':'paper';follow=prefs.follow!==false;
    speed=Math.max(.5,Math.min(2,Number(prefs.speed)||1));
    if(['voice','natural','relaxed'].includes(prefs.pauses))pauses=prefs.pauses;
    if(prefs.voices&&typeof prefs.voices==='object')voiceByOwner=prefs.voices;
  }catch{}
  function appearance(){
    document.documentElement.dataset.theme=theme;document.documentElement.style.setProperty('--reading-size',fontSize+'px');
    $('theme').textContent=theme==='dark'?'Paper theme':'Dark theme';$('theme').setAttribute('aria-pressed',String(theme==='dark'));
    $('font-size').textContent=fontSize;$('font-smaller').disabled=fontSize<=16;$('font-larger').disabled=fontSize>=32;
    $('follow').setAttribute('aria-pressed',String(follow));
    $('speech-speed').value=speed;$('speech-speed-value').textContent=Number(speed.toFixed(2))+'×';
    $('pauses').value=pauses;
    audio.defaultPlaybackRate=speed;audio.playbackRate=speed;
    try{localStorage.setItem('look-books-appearance',JSON.stringify({theme,fontSize,follow,speed,pauses,voices:voiceByOwner}))}catch{}
  }
  function focusPassage(smooth=false){
    const active=$('passage').querySelector('[aria-current="true"]');if(!active||!follow)return;
    const viewport=$('reading-body'),a=active.getBoundingClientRect(),v=viewport.getBoundingClientRect();
    viewport.scrollTo({top:viewport.scrollTop+a.top-v.top-Math.max(0,(viewport.clientHeight-active.offsetHeight)/2),
      behavior:smooth&&!matchMedia('(prefers-reduced-motion: reduce)').matches?'smooth':'auto'});
  }
  function highlight(){
    $('passage').querySelectorAll('[data-paragraph]').forEach(element=>{
      const active=Number(element.dataset.paragraph)===paragraph;
      if(active)element.setAttribute('aria-current','true');else element.removeAttribute('aria-current');
    });
    focusPassage(true);
  }
  function renderChapter(){
    const elements=[],images=content.images||[];
    for(let i=0;i<=content.paragraphs.length;i++){
      images.filter(image=>image.before===i).forEach(image=>{
        const figure=document.createElement('figure'),picture=document.createElement('img');
        picture.alt=image.alt||'Book illustration';picture.loading='lazy';picture.decoding='async';
        picture.src='/api/books/image?'+params({chapter,image:image.index});figure.append(picture);
        picture.onload=()=>focusPassage();
        picture.onerror=()=>{picture.remove();caption.textContent='Illustration unavailable'+(image.alt?': '+image.alt:'.')};
        const caption=document.createElement('figcaption');caption.textContent=image.alt||'';figure.append(caption);elements.push(figure);
      });
      if(i===content.paragraphs.length)break;
      const index=i+(content.start||0),p=document.createElement('p');p.className='reading-paragraph';p.dataset.paragraph=index;p.tabIndex=0;p.textContent=content.paragraphs[i];
      const select=()=>{const autoplay=playbackIntent;save();load(chapter,index,autoplay).then(()=>save()).catch(e=>status(e.message))};
      p.onclick=select;p.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();select()}};elements.push(p);
    }
    $('passage').replaceChildren(...elements);
  }
  function libraryView(){++generation;playbackIntent=false;requestedPosition=null;ahead.clear();audio.pause();save();$('reader').hidden=true;$('library').hidden=false;$('books-app').classList.remove('reading')}
  function status(text){$('status').textContent=text}
  async function api(route='',payload,signal){
    const response=await fetch('/api/books'+route,payload?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload),signal}:{cache:'no-store',signal});
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
    requestedPosition=c===undefined?null:{chapter:c,paragraph:p};
    const preparedTask=c===undefined?null:ahead.take(narrationRoute(c,p));
    if(c===undefined)ahead.clear();
    const mine=++generation;playbackIntent=autoplay;switchingAudio=true;audio.pause();audio.removeAttribute('src');audio.load();releaseAudio();
    status('Preparing your reading position…');
    const needContent=!content||content.legacy||c===undefined||c!==chapter;
    const prepared=preparedTask?await preparedTask:null;
    if(mine!==generation){if(prepared?.url)URL.revokeObjectURL(prepared.url);return}
    const value=prepared?.value||await api('/read?'+params({...(c===undefined?{}:{chapter:c,paragraph:p}),content:needContent?'1':'0'}));
    if(mine!==generation){if(prepared?.url)URL.revokeObjectURL(prepared.url);return}
    model=value;chapter=value.chapter;paragraph=value.paragraph;requestedPosition=null;
    $('reader').hidden=false;$('library').hidden=true;$('books-app').classList.add('reading');$('title').textContent=book.title;
    if(value.content){content=value.content;renderChapter()}
    else if(needContent){content={paragraphs:[value.text],images:[],start:paragraph,legacy:true};renderChapter()}
    highlight();
    $('where').textContent=`${value.chapters[chapter].title} · paragraph ${paragraph+1}/${value.chapters[chapter].paragraphs}`;
    $('chapters').replaceChildren(...value.chapters.map((row,i)=>{const o=document.createElement('option');o.value=i;o.textContent=row.title;return o}));$('chapters').value=chapter;
    const coverURL='/api/books/cover?'+params();
    if($('cover').getAttribute('src')!==coverURL){
      $('cover').hidden=false;$('cover').onerror=()=>{$('cover').hidden=true};$('cover').src=coverURL;
    }
    activeAudioURL=prepared?.url||'';
    audio.src=activeAudioURL||narrationRoute(chapter,paragraph);switchingAudio=false;
    audio.playbackRate=speed;
    const offset=c===undefined?(value.reading.offset||0):resumeOffset;
    audio.onloadedmetadata=()=>{if(mine!==generation)return;audio.playbackRate=speed;if(offset&&offset<audio.duration)audio.currentTime=offset};
    audio.onerror=()=>mine===generation&&status('Narration unavailable. Check that the book owner is reachable and has a speech voice and ffmpeg installed.');
    status('Ready. Press Play to prepare narration and listen on this device.');
    if(autoplay&&playbackIntent){status('Preparing narration…');await audio.play().catch(()=>{if(mine===generation){playbackIntent=false;status('Tap Play to continue listening.')}})}
  }
  async function open(row){
    ++libraryGeneration;playbackIntent=false;requestedPosition=null;ahead.clear();audio.pause();if(book)save();book=row;model=null;content=null;const mine=++generation;
    status('Loading narration voices…');
    let options;try{options=await api('/voices?'+params())}catch{options={voices:[]}}
    if(mine!==generation)return;
    const voices=options.voices||[];
    defaultVoice=options.default?.id||'';
    selectedVoice=voices.some(voice=>voice.id===voiceByOwner[book.node||'local'])?voiceByOwner[book.node||'local']:'';
    const standards=Object.entries(options.standard||{}).filter(([,voice])=>voice).map(([kind,voice])=>({...voice,name:'British '+kind+' — '+voice.name}));
    $('voice').replaceChildren(...[{id:'',name:options.default?'Default — '+options.default.name:'Default voice'},...standards,...voices.filter(voice=>!standards.some(row=>row.id===voice.id))].map(voice=>{
      const option=document.createElement('option');option.value=voice.id;option.textContent=voice.name+(voice.locale?' · '+voice.locale:'');return option;
    }));$('voice').value=selectedVoice;$('voice').disabled=!voices.length;
    await load();window.scrollTo({top:0,behavior:'auto'});focusPassage();
  }
  async function move(delta,autoplay=false){
    if(!model)return;save();const start=requestedPosition||{chapter,paragraph};
    const next=FabricBrowserViews.bookPosition(model.chapters,start.chapter,start.paragraph,delta);
    if(!next){if(delta>0){playbackIntent=false;ahead.clear();save(true);status('Book finished.')}return}
    await load(next.chapter,next.paragraph,autoplay);save();
  }
  function button(label,click){const b=document.createElement('button');b.textContent=label;b.onclick=()=>Promise.resolve().then(click).catch(e=>status(e.message));return b}
  function gutenbergId(row){
    if(/^[1-9]\d{0,8}$/.test(String(row.gutenberg_id||'')))return String(row.gutenberg_id);
    for(const key of ['source_url','url','identifier'])for(const value of String(row[key]||'').split('; ')){
      try{const u=new URL(value);if(!['www.gutenberg.org','gutenberg.org'].includes(u.hostname))continue;
        const m=u.pathname.match(/^\/ebooks\/([1-9]\d*)(?:\.opds|\.epub(?:\d)?(?:\.images|\.noimages)?)?\/?$/)||u.pathname.match(/^\/(?:cache\/epub|files)\/([1-9]\d*)\//);
        if(m)return m[1];
      }catch{}
    }
    return '';
  }
  function show(rows,discover=false){
    $('result-count').textContent=rows.length+(discover?(rows.length===1?' result':' results'):(rows.length===1?' book':' books'));
    $('items').replaceChildren(...rows.map(row=>{
      const id=gutenbergId(row),owned=discover&&id?catalog.find(book=>gutenbergId(book)===id):null;
      const b=button(row.title+(row.author?' — '+row.author:''),async()=>{
        if(row.kind==='subject')return discoverMode('subject',row.subject);
        if(!discover||owned)return open(owned||row);
        if(!confirm('Download '+row.title+' to this Fabric host’s books library?'))return;
        b.disabled=true;
        try{status('Downloading book…');const value=await api('/fetch',{url:row.url});await shelf();status('Added to your shelf: '+value.book.title)}finally{b.disabled=false}
      });
      if(owned){b.classList.add('owned');const badge=document.createElement('small');badge.textContent='Already on your shelf · Read';b.append(badge)}
      if(row.kind!=='subject'&&(!discover||id)){
        const thumb=document.createElement('span');thumb.className='book-thumb';thumb.setAttribute('aria-hidden','true');
        const img=document.createElement('img');img.alt='';img.loading='lazy';img.decoding='async';
        img.src=discover?'/api/books/discovery-cover?id='+id:'/api/books/cover?'+new URLSearchParams({target:row.node||'local',id:row.id});
        img.onerror=()=>{img.remove();thumb.textContent='BOOK'};thumb.append(img);b.prepend(thumb);
      }
      return b;
    }));
  }
  function shelfRows(){
    const terms=shelfQuery.toLocaleLowerCase().split(/\s+/).filter(Boolean);
    return catalog.filter(row=>terms.every(term=>(row.title+' '+(row.author||'')).toLocaleLowerCase().includes(term))).sort((a,b)=>{
      const title=()=>String(a.title).localeCompare(String(b.title),undefined,{numeric:true,sensitivity:'base'});
      if(sortOrder==='opened')return (b.reading?.updated||0)-(a.reading?.updated||0)||title();
      if(sortOrder==='added')return (b.added||0)-(a.added||0)||title();
      if(sortOrder==='author')return String(a.author||'').localeCompare(String(b.author||''),undefined,{sensitivity:'base'})||title();
      return title();
    });
  }
  function libraryControls(isShelf){
    $('shelf-sort').hidden=$('sort-label').hidden=!isShelf;
    $('shelf').setAttribute('aria-pressed',String(isShelf));$('discover').setAttribute('aria-pressed',String(!isShelf));
    $('load-more').hidden=true;
  }
  function renderShelf(){const rows=shelfRows();show(rows);status(rows.length?'Choose a book or continue reading.':'No matching book on your Fabric shelf. Use Search Gutenberg to find new books.')}
  async function shelf(query=''){
    const mine=++libraryGeneration;discovery=null;shelfQuery=query;libraryView();libraryControls(true);status('Loading Fabric shelf…');
    const value=await api();if(mine!==libraryGeneration)return;catalog=value.entries||[];renderShelf();
    if(value.errors?.length)status('Some book owners are unavailable. Showing the reachable shelf.');
  }
  async function discoverMode(mode,subject='',query='',more=false){
    const mine=++libraryGeneration;libraryView();libraryControls(false);status('Browsing Project Gutenberg…');
    const cursor=more?discovery?.next_index:1;
    if(!cursor)return;
    const [value,shelfValue]=await Promise.all([api('/discover?'+new URLSearchParams({mode,subject,query,start_index:cursor})),api()]);
    if(mine!==libraryGeneration)return;
    catalog=shelfValue.entries||[];
    const rows=more?[...discovery.entries,...(value.entries||[])]:value.entries||[];
    discovery={mode,subject,query,entries:rows,next_index:value.next_index};show(rows,true);
    $('load-more').hidden=!value.next_index;
    const label=mode==='subject'?subject:mode==='search'?'Search: '+query:mode==='new'?'New arrivals':mode==='subjects'?'Subjects':mode==='surprise'?'Surprise me':'Popular';
    status('Project Gutenberg · '+label+' · '+(rows.length?(mode==='subjects'?'Choose a subject.':'Select a title to download; dimmed titles are already on your shelf.'):'No matching books.')+(shelfValue.errors?.length?' Some book owners are unavailable; ownership checks are incomplete.':''));
  }
  async function resume(query=''){
    await shelf();const terms=query.toLocaleLowerCase().split(/\s+/).filter(Boolean);
    const rows=catalog.filter(row=>(query||!row.reading?.finished)&&terms.every(t=>(row.title+' '+row.author).toLocaleLowerCase().includes(t))).sort((a,b)=>(b.reading?.updated||0)-(a.reading?.updated||0));
    if(!rows.length){status('No matching book on your Fabric shelf. Use Search Gutenberg to find new books.');return}
    if(query&&new Set(rows.map(r=>r.id)).size>1){show(rows);status('Choose the book you meant.');return}
    if(!query&&!rows[0].reading?.updated){show(rows);status('Choose a book to begin reading.');return}
    await open(rows[0]);
  }
  $('shelf-sort').value=sortOrder;
  $('shelf-sort').onchange=()=>{sortOrder=$('shelf-sort').value;try{localStorage.setItem('look-books-shelf-sort',sortOrder)}catch{}renderShelf()};
  $('discover').onclick=()=>discoverMode('popular').catch(e=>status(e.message));
  $('load-more').onclick=()=>{if(discovery)discoverMode(discovery.mode,discovery.subject,discovery.query,true).catch(e=>{status(e.message);$('load-more').hidden=!discovery?.next_index})};
  $('shelf').onclick=()=>shelf().catch(e=>status(e.message));$('continue').onclick=()=>resume().catch(e=>status(e.message));
  $('library-back').onclick=()=>shelf().catch(e=>status(e.message));
  $('theme').onclick=()=>{theme=theme==='dark'?'paper':'dark';appearance()};
  $('font-smaller').onclick=()=>{fontSize=Math.max(16,fontSize-1);appearance();focusPassage()};
  $('font-larger').onclick=()=>{fontSize=Math.min(32,fontSize+1);appearance();focusPassage()};
  $('follow').onclick=()=>{follow=!follow;appearance();focusPassage()};appearance();
  $('speech-speed').oninput=()=>{speed=Number($('speech-speed').value);appearance()};
  audio.onratechange=()=>{const rate=Math.max(.5,Math.min(2,audio.playbackRate));if(rate!==speed||rate!==audio.playbackRate){speed=rate;appearance()}};
  $('pauses').onchange=()=>{pauses=$('pauses').value;appearance();if(!book||!model)return;const position=requestedPosition||{chapter,paragraph};save();load(position.chapter,position.paragraph,playbackIntent).then(()=>save()).catch(e=>status(e.message))};
  $('voice').onchange=()=>{if(!book||!model)return;const autoplay=playbackIntent;
    selectedVoice=$('voice').value;voiceByOwner[book.node||'local']=selectedVoice;appearance();
    const position=requestedPosition||{chapter,paragraph};
    save();load(position.chapter,position.paragraph,autoplay).then(()=>save()).catch(e=>status(e.message));
  };
  document.querySelectorAll('[data-mode]').forEach(b=>b.onclick=()=>discoverMode(b.dataset.mode).catch(e=>status(e.message)));
  $('search').onsubmit=e=>{e.preventDefault();const query=$('query').value.trim();(e.submitter?.value==='gutenberg'?discoverMode('search','',query):shelf(query)).catch(e=>status(e.message))};
  $('previous').onclick=()=>move(-1,playbackIntent).catch(e=>status(e.message));$('next').onclick=()=>move(1,playbackIntent).catch(e=>status(e.message));
  $('retry').onclick=()=>load(chapter,paragraph,true,audio.currentTime||0).catch(e=>status(e.message));
  $('chapters').onchange=()=>{const autoplay=playbackIntent;save();load(Number($('chapters').value),0,autoplay).then(()=>save()).catch(e=>status(e.message))};
  audio.onplay=()=>{playbackIntent=true;status('Preparing / playing narration…');save();focusPassage()};audio.onplaying=()=>{status('Reading on this device.');prepareNext()};
  audio.onpause=()=>{if(switchingAudio||!audio.paused)return;if(!audio.ended)playbackIntent=false;save();if(audio.currentSrc&&!audio.ended)status('Paused. Press Play to continue from here.')};
  audio.ontimeupdate=()=>{if(Date.now()-lastSave>5000){lastSave=Date.now();save();prepareNext()}};
  audio.onended=()=>move(1,true).catch(e=>status(e.message));
  window.addEventListener('pagehide',()=>{ahead.clear();releaseAudio();if(book&&model)fetch('/api/books/progress?'+params(),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:book.id,fields:{chapter,paragraph,offset:audio.currentTime||0}}),keepalive:true}).catch(()=>{})});
  try{await shelf();const q=new URLSearchParams(location.search);if(q.has('resume')||q.has('query'))await resume(q.get('query')||'')}catch(e){status(e.message)}
})();
