"""Decode actual ticket pixels and exercise the same bounded scanner used by Photo."""
import io
import json
from pathlib import Path
import subprocess
import threading
import urllib.request
import pytest
from PIL import Image
import photo_capture
from core import maintenance

ROOT=Path(__file__).resolve().parents[1]
NODE='/Users/jreno/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node'
TICKET='https://theater.example:8443/#ABCDEFGH2345'


def run_node(script,data=None):
    if not Path(NODE).exists():pytest.skip('Node unavailable')
    subprocess.run([NODE,'-e',script],input=json.dumps(data) if data else None,text=True,capture_output=True,check=True,cwd=ROOT)


@pytest.mark.parametrize('angle',[0,90,180,270])
def test_decoder_reads_ticket_from_camera_sized_frame(angle):
    import qrcode
    qr=qrcode.make(TICKET).convert('RGBA').rotate(angle).resize((245,245),Image.Resampling.BICUBIC)
    frame=Image.new('RGBA',(640,480),'white');frame.paste(qr,(170,110))
    data={'width':640,'height':480,'pixels':list(frame.tobytes()),'ticket':TICKET}
    run_node("""const assert=require('assert'),fs=require('fs'),decode=require('./look/qr_decoder.js');
    const d=JSON.parse(fs.readFileSync(0,'utf8'));
    const result=decode(new Uint8ClampedArray(d.pixels),d.width,d.height,{inversionAttempts:'attemptBoth'});
    assert.equal(result.data,d.ticket);""",data)


def test_scanner_uses_one_local_frame_and_stops_after_recognition():
    run_node("""const assert=require('assert');let calls=0,results=[];
    global.document={createElement:()=>({width:0,height:0,getContext:()=>({drawImage(){},getImageData:()=>({data:new Uint8ClampedArray(4)})})})};
    global.jsQR=()=>{calls++;return {data:'https://theater.example/#TICKET'}};
    const {Scanner}=require('./look/photo_qr.js');
    const scanner=new Scanner({readyState:4,videoWidth:1920,videoHeight:1080},x=>results.push(x),e=>{throw e});
    scanner.start();setTimeout(()=>{assert.equal(calls,1);assert.equal(results.length,1);assert(!scanner.active);assert(scanner.canvas.width<=1280)},30);
    """)


def test_qr_payloads_cannot_become_script_file_or_credential_links():
    run_node("""const assert=require('assert'),{destination}=require('./look/photo_qr.js');
    for(const value of ['javascript:alert(1)','data:text/html,bad','file:///etc/passwd','ftp://host/a','https://user:pass@host/','not a url','https://example.com/\\n'])assert.equal(destination(value),null,value);
    assert.equal(destination('https://theater.example:8443/#ABCDEFGH2345'),'https://theater.example:8443/#ABCDEFGH2345');
    """)


def test_decoder_assets_are_local_http_routes_and_installed_allowlist(tmp_path):
    server=photo_capture.CaptureServer(tmp_path)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        for name in ['qr_decoder.js','photo_qr.js']:
            with urllib.request.urlopen('http://127.0.0.1:'+str(server.server_port)+'/'+name) as response:
                assert response.headers['Content-Type'].startswith('text/javascript')
                assert response.read()==(ROOT/'look'/name).read_bytes()
            assert maintenance.allowed('.local/share/look/'+name)
            assert name in (ROOT/'install-look.sh').read_text()
        assert maintenance.allowed('.local/share/look/qr_decoder.LICENSE')
        assert not maintenance.allowed('.local/share/look/unrelated.js')
    finally:server.shutdown();server.server_close()


def test_recognized_ticket_reaches_open_button_and_stops_camera():
    script=photo_capture.PAGE.split('<script>')[1].split('</script>')[0]
    data={'script':script,'ticket':TICKET}
    run_node("""const assert=require('assert'),vm=require('vm'),fs=require('fs');const input=JSON.parse(fs.readFileSync(0,'utf8'));
    const elements=new Map(),opened=[];let scanner,stopped=0;
    const context={console,URL,location:{hash:'#session',pathname:'/'},navigator:{},window:{addEventListener(){},open:(...args)=>opened.push(args)},
      document:{getElementById:id=>{if(!elements.has(id))elements.set(id,{hidden:true,disabled:false,textContent:'',value:'',options:[]});return elements.get(id)}},
      LookPhotoQR:{destination:require('./look/photo_qr.js').destination,Scanner:class{constructor(video,result,error){this.onResult=result;scanner=this}stop(){}}}};
    vm.createContext(context);vm.runInContext(input.script,context);
    vm.runInContext('stream={getTracks:()=>[{stop:()=>globalThis.stopTrack()}]}',Object.assign(context,{stopTrack:()=>stopped++}));
    scanner.onResult(input.ticket);
    assert.equal(elements.get('qr-open').hidden,false);assert.equal(elements.get('qr-text').textContent,input.ticket);
    assert.equal(opened.length,0);elements.get('qr-open').onclick();
    assert.equal(opened[0][0],input.ticket);assert.equal(opened[0][2],'noopener,noreferrer');assert.equal(stopped,1);
    scanner.onResult('javascript:alert(1)');assert.equal(elements.get('qr-open').hidden,true);
    """,data)
