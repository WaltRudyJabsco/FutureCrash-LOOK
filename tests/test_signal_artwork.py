import importlib.util
import io
import subprocess
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]

def test_ascii_preferences_identity_cache_and_detached_results():
    script=r'''
const assert=require('node:assert/strict');const Art=require(process.argv[1]);
let images=[],stored={};const document={createElement(tag){const el={tag,setAttribute(){}};if(tag==='img')images.push(el);if(tag==='canvas')el.getContext=()=>({drawImage(){},getImageData(){return {data:new Uint8Array(48*24*4).fill(255)}}});return el}};
const art=new Art(document,{getItem:()=>null,setItem:(k,v)=>stored[k]=v});
assert.equal(art.mode,'ascii');
assert.equal(Art.ascii(new Uint8Array([0,0,0,255,255,255,255,255]),2,1),' @');
assert.equal(art.url({id:'a & b',node:'m3'},'3090'),'/api/media/cover?node=m3&id=a+%26+b');
assert.equal(art.url({},'3090'),'');
const old=art.render('/old'),current=art.render('/new');art.render('/new');assert.equal(images.length,2);
images[0].onload();images[1].onload();
Promise.resolve().then(()=>{assert.ok(old.textContent.startsWith('@'));assert.ok(current.textContent.startsWith('@'));art.setMode('image');assert.equal(stored['signal.artwork'],'image');assert.equal(art.render('/new').tag,'img');art.setMode('off');assert.equal(art.render('/new'),null);art.setMode('invalid');assert.equal(art.mode,'off')});
'''
    subprocess.run(['node','-e',script,str(ROOT/'signal-window/media-art.js')],check=True)

def test_cover_gateway_is_cover_only_and_bounded():
    spec=importlib.util.spec_from_file_location('signal_art_server',ROOT/'signal-window/server.py')
    server=importlib.util.module_from_spec(spec);spec.loader.exec_module(server)
    class Handler:
        def __init__(self): self.wfile=io.BytesIO();self.headers={};self.code=None
        def send_response(self,code): self.code=code
        def send_header(self,k,v): self.headers[k]=v
        def end_headers(self): pass
        def json(self,code,data): self.code=code
    class Response(io.BytesIO):
        headers={'Content-Type':'image/jpeg'}
    h=Handler()
    with patch.object(server.urllib.request,'urlopen',return_value=Response(b'cover')) as call:
        server._proxy_media_cover(h,'m3','track')
        assert '/v1/media/cover?target=m3&id=track' in call.call_args.args[0].full_url
    assert h.code==200 and h.wfile.getvalue()==b'cover'
    with patch.object(server.urllib.request,'urlopen',return_value=Response(b'x'*(8*1024*1024+1))):
        server._proxy_media_cover(h,'m3','track')
    assert h.code==502
    with patch.object(server.urllib.request,'urlopen') as call:
        server._proxy_media_cover(h,'m3','')
        call.assert_not_called()
    assert h.code==400
