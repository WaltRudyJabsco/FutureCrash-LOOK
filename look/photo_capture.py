"""Foreground browser camera with a short-lived, token-protected local capture edge."""
from __future__ import annotations
import argparse
import base64
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import secrets
import struct
import subprocess
import sys
import tempfile
import threading
import time
import urllib.parse
import webbrowser

MAX_PHOTO_BYTES=3*1024*1024
SESSION_SECONDS=30*60
MAX_PIXELS=16_000_000


def validate_png(data):
    if not 33<=len(data)<=MAX_PHOTO_BYTES or data[:8]!=b'\x89PNG\r\n\x1a\n' or data[12:16]!=b'IHDR':
        raise ValueError('Capture must be a PNG image up to 3 MiB')
    width,height=struct.unpack('>II',data[16:24])
    if not width or not height or width*height>MAX_PIXELS:raise ValueError('Photo dimensions are too large')
    return width,height


def save_photo(data,directory,system_clipboard=True):
    validate_png(data)
    import clipboard_items,clipboard_shelf,screen_shot
    directory=Path(directory).expanduser().resolve();directory.mkdir(parents=True,exist_ok=True,mode=0o700)
    name='Photo-'+time.strftime('%Y%m%d-%H%M%S')+'-'+secrets.token_hex(3)+'.png'
    path=directory/name
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'wb') as stream:stream.write(data)
    result={'path':str(path),'shelf':False,'clipboard':False}
    shelf=None
    try:
        shelf=clipboard_shelf.Shelf()
        result['shelf']=shelf.observe(clipboard_items.pack(data,name,'image/png'))
    except (OSError,ValueError,clipboard_shelf.sqlite3.Error) as exc:result['shelf_error']=str(exc)
    finally:
        if shelf is not None:shelf.close()
    if not system_clipboard:return result
    try:screen_shot.copy_image(path);result['clipboard']=True
    except (OSError,ValueError,subprocess.SubprocessError) as exc:result['clipboard_error']=str(exc)
    return result


class CaptureServer(ThreadingHTTPServer):
    daemon_threads=True

    def __init__(self,directory):
        super().__init__(('127.0.0.1',0),CaptureHandler)
        self.token=secrets.token_urlsafe(32)
        self.directory=directory
        self.finished=threading.Event()
        self.deadline=time.monotonic()+SESSION_SECONDS
        self.timeout=1
        self.capture_lock=threading.Lock()


class CaptureHandler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass

    def reply(self,status,value,ctype='application/json'):
        data=value.encode() if isinstance(value,str) else json.dumps(value).encode()
        self.send_response(status)
        self.send_header('Content-Type',ctype);self.send_header('Content-Length',str(len(data)))
        self.send_header('Cache-Control','no-store');self.send_header('Referrer-Policy','no-referrer')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Permissions-Policy','camera=(self), microphone=()')
        self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src 'self' blob:; media-src 'self' blob:; frame-ancestors 'none'; base-uri 'none'")
        self.end_headers();self.wfile.write(data)

    def do_GET(self):
        if self.path!='/':return self.reply(404,{'error':'Unknown capture route'})
        return self.reply(200,PAGE,'text/html; charset=utf-8')

    def do_POST(self):
        try:
            origin=self.headers.get('Origin','')
            expected='http://127.0.0.1:'+str(self.server.server_port)
            if origin!=expected:raise PermissionError('Open the local Photo window directly')
            supplied=self.headers.get('X-LOOK-Photo-Token','')
            if not hmac.compare_digest(supplied,self.server.token):raise PermissionError('This Photo session is unavailable; run lk photo again')
            if time.monotonic()>self.server.deadline:raise PermissionError('Photo session expired; run lk photo again')
            if self.path=='/close':
                self.server.finished.set();return self.reply(200,{'closed':True})
            if self.path!='/capture':return self.reply(404,{'error':'Unknown capture route'})
            size=int(self.headers.get('Content-Length','0'))
            if self.headers.get('Content-Type')!='image/png' or not 0<size<=MAX_PHOTO_BYTES:raise ValueError('Use a PNG photo up to 3 MiB')
            self.connection.settimeout(15)
            data=self.rfile.read(size)
            if len(data)!=size:raise ValueError('Capture upload was incomplete')
            with self.server.capture_lock:result=save_photo(data,self.server.directory)
            return self.reply(200,result)
        except PermissionError as exc:return self.reply(403,{'error':str(exc)})
        except (ValueError,OSError) as exc:return self.reply(400,{'error':str(exc)})


def serve(directory,announce):
    server=CaptureServer(directory)
    try:
        url='http://127.0.0.1:'+str(server.server_port)+'/#'+server.token
        Path(announce).write_text(json.dumps({'url':url,'pid':os.getpid()}))
        while not server.finished.is_set() and time.monotonic()<server.deadline:
            server.handle_request()
    finally:server.server_close()


def main(argv=None):
    parser=argparse.ArgumentParser(prog='lk photo',description='Open a camera preview, choose a source and save captures to Pictures/LOOK Photos and LK Clip.')
    parser.add_argument('--output-dir',type=Path,default=Path.home()/'Pictures/LOOK Photos')
    parser.add_argument('--serve',action='store_true',help=argparse.SUPPRESS)
    parser.add_argument('--announce',help=argparse.SUPPRESS)
    args=parser.parse_args(argv)
    if args.serve:
        if not args.announce:raise ValueError('Missing capture session announcement')
        serve(args.output_dir,args.announce);return 0
    with tempfile.TemporaryDirectory(prefix='look-photo-') as directory:
        announce=Path(directory)/'session.json'
        process=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'--serve','--announce',str(announce),'--output-dir',str(args.output_dir.expanduser())],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
        for _ in range(100):
            if announce.exists():break
            if process.poll() is not None:raise ValueError('The local camera session could not start')
            time.sleep(.05)
        else:
            process.terminate();raise ValueError('Camera session startup timed out')
        value=json.loads(announce.read_text())
        opened=webbrowser.open(value['url'])
        print('Photo camera opened. Choose Start camera, then Take photo.' if opened else 'Photo camera is ready in your browser.')
        print('Photos save to '+str(args.output_dir.expanduser())+' and LK Clip.')
        if not opened:print('Open this local capture link: '+value['url'])
    return 0


PAGE=r'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>LOOK Photo</title><style>
:root{color-scheme:dark}*{box-sizing:border-box}body{margin:auto;padding:24px;max-width:1000px;background:#10191d;color:#eee9dc;font:17px/1.5 system-ui}header,.tools{display:flex;gap:12px;align-items:center;flex-wrap:wrap;justify-content:space-between}h1{font:normal 30px Georgia;color:#c6a66f}video,img{width:100%;max-height:68vh;object-fit:contain;background:#080c0e;border-radius:10px}button,select{font:inherit;padding:12px;background:#1d2b31;color:inherit;border:1px solid #60757d;border-radius:6px;min-height:44px}button{cursor:pointer}button.primary{background:#c6a66f;color:#10191d;font-weight:600}button:disabled{opacity:.5}button:focus-visible,select:focus-visible{outline:2px solid #83c9f4}p{color:#b4c0c3;overflow-wrap:anywhere}.tools{justify-content:flex-start;margin:16px 0}[hidden]{display:none!important}@media(max-width:600px){body{padding:14px}select{max-width:100%}}
</style><header><h1>LOOK Photo</h1><button id="done">Done</button></header><div class="tools"><label>Camera <select id="camera"><option value="">Default camera</option></select></label><button id="start">Start camera</button><button id="capture" class="primary" disabled>Take photo</button><button id="retake" hidden>Back to camera</button></div><p id="status" role="status">Start camera to allow access. Connected cameras appear in the source list.</p><video id="video" autoplay playsinline muted></video><img id="photo" alt="Your captured photo" hidden><p id="saved"></p><script>
const $=id=>document.getElementById(id),v=$('video');let token=location.hash.slice(1),stream=null,busy=false,closed=false,preview=null;
function message(text){$('status').textContent=text}
function stop(){if(stream)for(const track of stream.getTracks())track.stop();stream=null;v.srcObject=null;$('capture').disabled=true}
async function devices(){if(!navigator.mediaDevices)return;const selected=$('camera').value;const list=await navigator.mediaDevices.enumerateDevices();$('camera').replaceChildren();const first=document.createElement('option');first.value='';first.textContent='Default camera';$('camera').append(first);for(const device of list.filter(x=>x.kind==='videoinput')){const option=document.createElement('option');option.value=device.deviceId;option.textContent=device.label||'Camera '+$('camera').options.length;$('camera').append(option)}if([...$('camera').options].some(o=>o.value===selected))$('camera').value=selected}
async function start(){if(busy||closed)return;busy=true;$('start').disabled=true;$('camera').disabled=true;stop();try{if(!navigator.mediaDevices?.getUserMedia)throw Error('Camera access requires a supported browser on this computer. Open the local link printed by lk photo.');const id=$('camera').value;stream=await navigator.mediaDevices.getUserMedia({video:{...(id?{deviceId:{exact:id}}:{}),width:{ideal:1920},height:{ideal:1080}},audio:false});v.srcObject=stream;await v.play();await devices();$('photo').hidden=true;v.hidden=false;$('capture').disabled=false;message('Ready · '+(stream.getVideoTracks()[0]?.label||'Default camera'))}catch(e){message(e.name==='NotAllowedError'?'Camera permission was denied. Allow this page in your browser’s camera settings and try again.':e.name==='NotFoundError'?'No camera found. Connect a camera and choose Start camera.':e.message)}finally{busy=false;$('start').disabled=false;$('camera').disabled=false}}
async function capture(){if(busy||!stream)return;busy=true;$('capture').disabled=true;try{if(!v.videoWidth)throw Error('The camera is still starting');const canvas=document.createElement('canvas');const ratio=Math.min(1,1920/Math.max(v.videoWidth,v.videoHeight));canvas.width=Math.round(v.videoWidth*ratio);canvas.height=Math.round(v.videoHeight*ratio);canvas.getContext('2d').drawImage(v,0,0,canvas.width,canvas.height);let blob=await new Promise(r=>canvas.toBlob(r,'image/png'));while(blob&&blob.size>3145728&&canvas.width>320){const smaller=document.createElement('canvas');smaller.width=Math.round(canvas.width*.8);smaller.height=Math.round(canvas.height*.8);smaller.getContext('2d').drawImage(canvas,0,0,smaller.width,smaller.height);canvas.width=smaller.width;canvas.height=smaller.height;canvas.getContext('2d').drawImage(smaller,0,0);blob=await new Promise(r=>canvas.toBlob(r,'image/png'))}if(!blob||blob.size>3145728)throw Error('Could not prepare a clipboard-sized photo');message('Saving photo…');const response=await fetch('/capture',{method:'POST',headers:{'Content-Type':'image/png','X-LOOK-Photo-Token':token},body:blob});const data=await response.json();if(!response.ok)throw Error(data.error);if(preview)URL.revokeObjectURL(preview);preview=URL.createObjectURL(blob);$('photo').src=preview;$('photo').hidden=false;v.hidden=true;$('retake').hidden=false;$('saved').textContent='Saved '+data.path;message(data.clipboard?'Saved · copied to clipboard'+(data.shelf?' · added to LK Clip':''):data.shelf?'Saved · added to LK Clip. System clipboard unavailable.':'Saved. Clipboard unavailable.')}catch(e){message(e.message)}finally{busy=false;$('capture').disabled=!stream}}
$('start').onclick=start;$('camera').onchange=start;$('capture').onclick=capture;$('retake').onclick=()=>{$('photo').hidden=true;v.hidden=false;$('retake').hidden=true};$('done').onclick=async()=>{if(busy)return;closed=true;stop();$('start').disabled=true;$('camera').disabled=true;try{await fetch('/close',{method:'POST',headers:{'X-LOOK-Photo-Token':token}})}catch{}message('Camera closed. You can close this tab.')};window.addEventListener('pagehide',stop);navigator.mediaDevices?.addEventListener('devicechange',()=>devices().catch(e=>message(e.message)));devices().catch(()=>{});
</script></html>'''

if __name__=='__main__':
    try:raise SystemExit(main())
    except (OSError,ValueError) as exc:print('Photo: '+str(exc));raise SystemExit(1)
