/* Camera QR scanning. Decoder runs locally; decoded content remains untrusted data. */
(function(root){
  function destination(value){
    const raw=String(value||'');
    if(/[\u0000-\u001f\u007f]/.test(raw))return null;
    const text=raw.trim();
    if(text.length>4096||/[\u0000-\u0020\u007f]/.test(text))return null;
    try{
      const url=new URL(text);
      if(!['https:','http:'].includes(url.protocol)||!url.hostname||url.username||url.password)return null;
      return url.href;
    }catch{return null}
  }

  class Scanner{
    constructor(video,onResult,onError){
      this.video=video;this.onResult=onResult;this.onError=onError;
      this.canvas=document.createElement('canvas');
      this.context=this.canvas.getContext('2d',{willReadFrequently:true});
      this.active=false;this.timer=null;
    }
    start(){
      this.stop();this.active=true;
      const tick=()=>{
        if(!this.active)return;
        try{
          const video=this.video;
          if(video.readyState>=2&&video.videoWidth&&video.videoHeight){
            const ratio=Math.min(1,1280/Math.max(video.videoWidth,video.videoHeight));
            const width=Math.max(1,Math.round(video.videoWidth*ratio));
            const height=Math.max(1,Math.round(video.videoHeight*ratio));
            if(this.canvas.width!==width||this.canvas.height!==height){this.canvas.width=width;this.canvas.height=height}
            this.context.drawImage(video,0,0,width,height);
            const image=this.context.getImageData(0,0,width,height);
            const code=root.jsQR(image.data,width,height,{inversionAttempts:'attemptBoth'});
            if(code?.data){this.stop();this.onResult(code.data);return}
          }
        }catch(error){this.stop();this.onError(error);return}
        this.timer=setTimeout(tick,350);
      };
      this.timer=setTimeout(tick,0);
    }
    stop(){this.active=false;clearTimeout(this.timer);this.timer=null}
  }
  const api={destination,Scanner};
  if(typeof module!=='undefined'&&module.exports)module.exports=api;
  else root.LookPhotoQR=api;
})(typeof window!=='undefined'?window:globalThis);
