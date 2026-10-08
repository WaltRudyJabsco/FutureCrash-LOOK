import subprocess
from pathlib import Path


def test_browser_transport_ownership_metadata_and_position():
    module = Path(__file__).resolve().parents[1] / 'signal-window/media-session.js'
    script = r'''
const assert=require('node:assert/strict');
const MediaSession=require(process.argv[1]);
let handlers={},calls=[],positions=[];
const session={setActionHandler:(name,fn)=>{if(name==='stop')throw Error('unsupported');handlers[name]=fn},setPositionState:x=>positions.push(x)};
let snapshot={count:2,state:'playing',index:0,entry:{title:'Lola',artist:'The Kinks',album:'Show-Biz'},position:15,duration:100};
const bridge=new MediaSession({mediaSession:session},class Metadata{constructor(x){Object.assign(this,x)}},()=>snapshot,(...args)=>calls.push(args));
bridge.update(true);
assert.equal(session.metadata.title,'Lola');
assert.equal(session.playbackState,'playing');
handlers.nexttrack({});handlers.previoustrack({});handlers.pause({});handlers.seekforward({seekOffset:20});handlers.seekto({seekTime:80});
assert.deepEqual(calls,[['next'],['prev'],['pause'],['seek',35],['seek',80]]);
const staleHandler=handlers.nexttrack;
bridge.update(false);
assert.equal(handlers.nexttrack,null);assert.equal(session.metadata,null);
staleHandler({});assert.equal(calls.length,5);
snapshot={...snapshot,state:'paused',position:500,index:1,entry:{title:'Next'}};
bridge.update(true);
assert.equal(session.playbackState,'paused');assert.equal(session.metadata.title,'Next');
assert.equal(positions.at(-1).position,100);
snapshot={...snapshot,state:'stopped'};bridge.update(true);
assert.equal(handlers.play,null);
new MediaSession({},null,()=>snapshot,()=>{}).update(true);
'''
    subprocess.run(['node', '-e', script, str(module)], check=True)
