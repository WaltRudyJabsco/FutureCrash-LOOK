import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]


def helper(path):
    text=path.read_text();start=text.index('function createMediaFullscreen(doc)')
    end=text.index('\nconst ',start)
    return text[start:end].strip()


def test_fullscreen_edges_match_in_both_surfaces():
    assert helper(ROOT/'signal-window/app.js')==helper(ROOT/'albert/index.html')


def test_fullscreen_preserves_media_and_supports_native_exit_fallback_and_cleanup():
    source=helper(ROOT/'signal-window/app.js')
    script=source+r'''
const assert=require('node:assert/strict');
const classes=()=>({values:new Set(),add(x){this.values.add(x)},remove(x){this.values.delete(x)},contains(x){return this.values.has(x)}});
function fixture(){
 const events={},button={textContent:'',isConnected:true,disabled:false,hidden:false,focus(){doc.activeElement=this},setAttribute(k,v){this[k]=v},closest(){return target}};
 const video={controls:false,dataset:{},currentTime:42,src:'movie',addEventListener(k,fn){events[k]=fn}};
 const target={classList:classes(),querySelector(q){return q==='video'?video:button},querySelectorAll(){return [button,video]},contains(x){return x===button||x===video}};
 const doc={body:{classList:classes()},activeElement:button,querySelectorAll(){return [button]},addEventListener(k,fn){events[k]=fn},fullscreenElement:null};
 return {events,button,video,target,doc};
}
(async()=>{
 let f=fixture(),calls=0;
 f.target.requestFullscreen=async()=>{calls++;f.doc.fullscreenElement=f.target};
 f.doc.exitFullscreen=async()=>{f.doc.fullscreenElement=null;f.events.fullscreenchange()};
 let view=createMediaFullscreen(f.doc);await view.toggle(f.target);
 assert.equal(calls,1);assert.equal(f.button.textContent,'Exit full screen');assert.equal(f.video.controls,true);
 assert.equal(f.video.currentTime,42);assert.equal(f.video.src,'movie');
 await view.exit();assert.equal(view.active(f.target),false);assert.equal(f.video.controls,false);assert.equal(f.button.textContent,'Full screen');
 await view.toggle(f.target);f.doc.fullscreenElement=null;f.events.fullscreenchange();
 assert.equal(view.active(f.target),false);assert.equal(f.video.controls,false);
 f=fixture();view=createMediaFullscreen(f.doc);
 f.video.webkitEnterFullscreen=()=>{f.video.webkitDisplayingFullscreen=true};
 f.video.webkitExitFullscreen=()=>{f.video.webkitDisplayingFullscreen=false;f.events.webkitendfullscreen()};
 await view.toggle(f.target);assert.equal(f.video.webkitDisplayingFullscreen,true);await view.exit();assert.equal(f.video.controls,false);
 f=fixture();view=createMediaFullscreen(f.doc);f.target.requestFullscreen=()=>Promise.reject(Error('blocked'));
 await view.toggle(f.target);assert.equal(f.target.classList.contains('media-fullscreen'),true);
 f.events.keydown({key:'Escape',preventDefault(){}});await Promise.resolve();assert.equal(view.active(f.target),false);
 await view.toggle(f.target);view.closeWithin({contains(x){return x===f.target}});await Promise.resolve();assert.equal(f.doc.body.classList.contains('media-fullscreen-open'),false);
 // Audio-only full screen works without inventing a video/audio playback graph.
 f=fixture();f.target.querySelector=q=>q==='video'?null:f.button;view=createMediaFullscreen(f.doc);
 await view.toggle(f.target);assert.equal(view.active(f.target),true);await view.exit();
})();
'''
    subprocess.run(['node','-e',script],check=True)


def test_surfaces_have_visible_controls_and_cleanup_without_web_audio():
    signal=(ROOT/'signal-window/app.js').read_text();albert=(ROOT/'albert/index.html').read_text()
    assert 'head.append(full)' in signal and 'signalFullscreen.refresh()' in signal
    assert 'signalFullscreen.closeWithin(mediaPanel)' in signal
    assert 'albertFullscreen.closeWithin(root)' in albert
    assert albert.count('data-media-fullscreen onclick=')==2
    assert 'createMediaElementSource' not in signal+albert
