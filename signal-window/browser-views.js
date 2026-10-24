/* Shared by Signal and Albert: browser-local views, never compute-worker windows. */
(function(root){
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
      finish(payload){
        const images=imageArtifacts(payload);
        if(!wanted||!images.length){this.cancel();return {images,opened:false}}
        try{if(tab&&!tab.closed){tab.location.replace(images[0].url);tab=null;return {images,opened:true}}}catch{}
        return {images,opened:false};
      },
      cancel(){try{if(tab&&!tab.closed)tab.close()}catch{}tab=null}
    };
  }
  function fabricCommand(text){return /^(?:\/fabric|(?:please\s+)?(?:show|open)(?:\s+(?:me|our|the))?\s+fabric(?:\s+(?:dash|dashboard|status))?)[.!?]?$/i.test(String(text||'').trim())}
  function openFabric(){
    const url=new URL('/fabric.html',root.location.href).href;
    try{root.open(url,'_blank','noopener')}catch{}
    return url;
  }
  root.FabricBrowserViews={beginImage,imageArtifacts,imageRequest,fabricCommand,openFabric};
})(globalThis);
