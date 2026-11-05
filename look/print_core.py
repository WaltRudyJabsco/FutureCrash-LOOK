"""Local CUPS edge and durable, single-submission print plans.

Printing consumes paper: planning never invokes lp; an uncertain submission is
never retried automatically. Device attachment alone changes no configuration.
"""
import base64
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import sys
import time
import uuid
from urllib.parse import urlsplit

MAX_INPUT_BYTES=3*1024*1024
MAX_PENDING_BYTES=32*1024*1024
MAX_IMAGE_PIXELS=16_000_000
MAX_RASTER_HEIGHT=4096
COMMAND_TIMEOUT=20
PLAN_LIFETIME=24*60*60
QUEUE_PATTERN=r'[A-Za-z0-9_][A-Za-z0-9_.-]{0,126}'


def name(value):
    if not isinstance(value,str) or not re.fullmatch(QUEUE_PATTERN,value):raise ValueError('Use an exact CUPS queue name from lk print list')
    return value


def run(args,data=None):
    tool=shutil.which(args[0])
    if not tool:raise RuntimeError('Missing '+args[0]+'; install/enable CUPS using this system’s printer settings')
    env=dict(os.environ,LC_ALL='C',LANG='C')
    # Each Fabric owner controls its own spooler, never an inherited remote server.
    env.pop('CUPS_SERVER',None)
    result=subprocess.run([tool,*args[1:]],input=data,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=COMMAND_TIMEOUT,env=env)
    if result.returncode:raise RuntimeError(result.stderr.decode(errors='replace').strip() or args[0]+' failed')
    return result.stdout.decode(errors='replace').strip()


def profiles():
    try:return json.loads((Path.home()/'.config/look/printers.json').read_text())
    except FileNotFoundError:return {}


DISCOVERY_CACHE_SECONDS=60
DISCOVERY_BROWSE_SECONDS=2
_DEVICE_CACHE=(0,[])


def discovered_devices():
    global _DEVICE_CACHE
    if time.monotonic()-_DEVICE_CACHE[0]<DISCOVERY_CACHE_SECONDS:return _DEVICE_CACHE[1]
    rows=[]
    if shutil.which('ippfind'):
        try:
            output=run(['ippfind','-T',str(DISCOVERY_BROWSE_SECONDS),'--exec',sys.executable,'-c','import json,sys;print(json.dumps(sys.argv[1:]))','{service_uri}','{txt_UUID}','{service_name}',';'])
            for line in output.splitlines():
                try:
                    uri,uuid,label=json.loads(line);rows.append({'uri':uri,'uuid':uuid,'label':label})
                except (ValueError,TypeError):continue
        except (OSError,RuntimeError,subprocess.SubprocessError):pass
    if not rows:
        # Minimal Linux CUPS installs may expose Bonjour through lpinfo without
        # shipping ippfind. Those observed UUIDs remain useful for class routes.
        try:
            from urllib.parse import urlsplit,parse_qs,unquote
            for line in run(['lpinfo','-v']).splitlines():
                parts=line.split(None,1)
                if len(parts)!=2:continue
                uri=parts[1];parsed=urlsplit(uri)
                ident=(parse_qs(parsed.query).get('uuid') or [''])[0]
                if parsed.scheme=='dnssd' and re.fullmatch(r'[0-9a-fA-F-]{36}',ident):rows.append({'uri':uri,'uuid':ident,'label':unquote(parsed.netloc).split('._')[0]})
        except (OSError,RuntimeError,ValueError,subprocess.SubprocessError):pass
    _DEVICE_CACHE=(time.monotonic(),rows)
    return rows


def catalog():
    try:output=run(['lpstat','-p'])
    except RuntimeError as error:
        return {'printers':[],'available':False,'warning':str(error),'setup':'lk print discover; use system printer settings to install/enable CUPS'}
    rows=[];configured=profiles()
    try:
        connections={match[1]:match[2] for line in run(['lpstat','-v']).splitlines() if (match:=re.match(r'device for (\S+): (.+)',line))}
    except (OSError,RuntimeError,subprocess.SubprocessError):connections={}
    from print_destinations import device
    observed=discovered_devices() if connections else []
    for line in output.splitlines():
        match=re.match(r'printer (\S+) (.*)',line)
        if match:rows.append({'name':match[1],'status':match[2],'profile':configured.get(match[1],{'kind':'document'}),'device':device(connections.get(match[1],''),observed)})
    return {'printers':rows,'available':True}


def require_queue(queue):
    if not isinstance(queue,str) or not 0<len(queue)<=128:raise ValueError('Choose a printer queue or configured nickname')
    value=catalog();configured=profiles()
    exact=[row for row in value['printers'] if row['name']==queue]
    matches=exact or [row for row in value['printers'] if configured.get(row['name'],{}).get('label','').casefold()==queue.casefold()]
    if len(matches)>1:
        from print_destinations import consolidate,route
        groups=consolidate([dict(row,node='local') for row in matches])
        if len(groups)!=1 or not groups[0]['identity_verified']:raise ValueError('Nickname is ambiguous; choose an exact queue name')
        return name(route(groups[0],'local')['name'])
    if not matches:raise ValueError('Queue unavailable: '+queue+'. '+value.get('warning','Run lk print list or configure it in system printer settings.'))
    return name(matches[0]['name'])


def update_profile(queue,fields):
    folder=Path.home()/'.config/look';folder.mkdir(parents=True,exist_ok=True)
    import fcntl
    with (folder/'.printers.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        values=profiles()
        conflicts=[key for key,row in values.items() if key!=queue and row.get('label','').casefold()==fields.get('label','').casefold()] if 'label' in fields else []
        if conflicts:
            from print_destinations import consolidate
            groups=consolidate([dict(row,node='local') for row in catalog()['printers'] if row['name'] in {queue,*conflicts}])
            if len(groups)!=1 or not groups[0]['identity_verified']:raise ValueError('Nickname already belongs to another local queue')
        value=dict(values.get(queue,{'kind':'document'}),**fields);values[queue]=value
        temporary=folder/('.printers-'+uuid.uuid4().hex)
        try:
            with temporary.open('x') as out:
                os.chmod(temporary,0o600);json.dump(values,out)
            os.replace(temporary,folder/'printers.json')
        finally:temporary.unlink(missing_ok=True)
    return value


def nickname(queue,label,confirm=False):
    queue=require_queue(queue)
    if not isinstance(label,str) or not label.strip() or len(label)>80 or any(ord(c)<32 or ord(c)==127 for c in label):raise ValueError('Use a short printable nickname')
    label=label.strip()
    if confirm is not True:return {'applied':False,'queue':queue,'proposed_nickname':label}
    return {'applied':True,'queue':queue,'profile':update_profile(queue,{'label':label})}


def configure_profile(queue,kind='document',width=384,columns=32,confirm=False):
    queue=require_queue(queue)
    if kind not in {'document','escpos'}:raise ValueError('Choose document or escpos')
    if type(width) is not int or not 128<=width<=832 or width%8:raise ValueError('Printable width must be 128–832 dots in multiples of 8; check the printer manual')
    if type(columns) is not int or not 16<=columns<=80:raise ValueError('Columns must be 16–80')
    value={'kind':kind,'width':width,'columns':columns}
    if confirm is not True:return {'applied':False,'queue':queue,'proposed_profile':dict(profiles().get(queue,{}),**value)}
    return {'applied':True,'queue':queue,'profile':update_profile(queue,value)}


def add_queue(queue,uri,driver='everywhere',confirm=False):
    name(queue)
    if not isinstance(uri,str) or any(ord(c)<33 for c in uri):raise ValueError('Invalid printer URI')
    parsed=urlsplit(uri)
    if parsed.scheme not in {'ipp','ipps','usb','socket','lpd','dnssd'} or not parsed.netloc or parsed.username or parsed.password:raise ValueError('Use a printer URI from discovery, without embedded credentials')
    if driver not in {'everywhere','raw'}:raise ValueError('Choose driver everywhere or raw (only for a verified ESC/POS device)')
    if driver=='everywhere' and parsed.scheme not in {'ipp','ipps'}:raise ValueError('Driverless setup requires ipp/ipps; use system settings for vendor drivers')
    if any(row['name']==queue for row in catalog()['printers']):raise ValueError('Queue already exists; use system printer settings to edit it')
    args=['lpadmin','-p',queue,'-E','-v',uri,'-m',driver]
    if confirm is not True:return {'applied':False,'command':args,'note':'Creates a queue only; sharing, system default and device profile are unchanged. CUPS may require local administrator permission.'}
    run(args)
    return {'applied':True,'queue':queue,'catalog':catalog()}


def options(queue):
    queue=require_queue(queue);return {'queue':queue,'options':run(['lpoptions','-p',queue,'-l'])}
def jobs(queue):
    queue=require_queue(queue);return {'queue':queue,'jobs':run(['lpstat','-W','all','-o',queue])}


def cancel(queue,job,confirm=False):
    queue=require_queue(queue)
    if not isinstance(job,str) or not re.fullmatch(re.escape(queue)+r'-[0-9]+',job):raise ValueError('Use the exact queue-N job ID')
    if confirm is not True:return {'cancelled':False,'job':job,'note':'Confirm to request cancellation; pages already printed cannot be recalled.'}
    run(['cancel',job]);return {'job':job,'state':'cancellation_requested'}


def print_options(value):
    value=value or {}
    if not isinstance(value,dict) or set(value)-{'copies','pages','media','sides'}:raise ValueError('Unsupported print options')
    result={};copies=value.get('copies',1)
    if type(copies) is not int or not 1<=copies<=20:raise ValueError('Copies must be 1–20')
    result['copies']=copies
    if value.get('pages'):
        if not isinstance(value['pages'],str) or not re.fullmatch(r'[1-9][0-9]{0,5}(?:-[1-9][0-9]{0,5})?(?:,[1-9][0-9]{0,5}(?:-[1-9][0-9]{0,5})?)*',value['pages']):raise ValueError('Use page ranges such as 1-3,5')
        for part in value['pages'].split(','):
            pair=part.split('-')
            if len(pair)==2 and int(pair[0])>int(pair[1]):raise ValueError('Page ranges must ascend')
        result['pages']=value['pages']
    if value.get('media'):
        if not isinstance(value['media'],str) or not re.fullmatch(r'[A-Za-z0-9_.-]{1,80}',value['media']):raise ValueError('Choose an exact media keyword from printer options')
        result['media']=value['media']
    if value.get('sides'):
        if value['sides'] not in {'one-sided','two-sided-long-edge','two-sided-short-edge'}:raise ValueError('Invalid sides')
        result['sides']=value['sides']
    return result


def receipt_text(text,columns):
    import textwrap
    if not isinstance(text,str) or not text.strip():raise ValueError('Receipt text is empty')
    if any(ord(c)<32 and c not in '\n\t' or ord(c)==127 for c in text):raise ValueError('Receipt text cannot contain printer control codes')
    text=text.translate(str.maketrans({'’':"'",'‘':"'",'“':'"','”':'"','–':'-','—':'--','…':'...','\u00a0':' '}))
    try:
        lines=['\n'.join(textwrap.wrap(line.expandtabs(4),columns) or ['']) for line in text.splitlines()]
        return ('\n'.join(lines)+'\n\n\n').encode('cp437',errors='strict')
    except UnicodeEncodeError as error:raise ValueError('This receipt text needs unsupported characters; use a raster image or a document printer') from error


def receipt_image(data,width):
    try:from PIL import Image,ImageOps
    except ImportError as error:raise RuntimeError('Receipt image preparation needs Pillow; text receipts work without it') from error
    with Image.open(io.BytesIO(data)) as source:
        if source.width*source.height>MAX_IMAGE_PIXELS:raise ValueError('Receipt image is too large')
        image=ImageOps.exif_transpose(source).convert('RGBA')
        paper=Image.new('RGBA',image.size,'white');paper.alpha_composite(image);image=paper.convert('L')
        height=max(1,round(image.height*min(width,image.width)/image.width))
        if height>MAX_RASTER_HEIGHT:raise ValueError('Receipt image is too tall; crop it first')
        image=image.resize((min(width,image.width),height))
        padded=Image.new('L',((image.width+7)//8*8,height),255);padded.paste(image)
        # ESC/POS GS v 0 uses a set bit for black; Pillow mode 1 uses it for white.
        raster=bytes(byte^255 for byte in padded.convert('1').tobytes());stride=padded.width//8
        return b'\x1dv0\x00'+stride.to_bytes(2,'little')+height.to_bytes(2,'little')+raster+b'\n\n\n'


class Spool:
    def __init__(self):
        root=Path.home()/'.local/share/look/print';root.mkdir(parents=True,exist_ok=True,mode=0o700)
        os.chmod(root,0o700)
        self.path=root/'jobs.sqlite3'
        with self.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, created REAL, state TEXT, meta TEXT, payload BLOB, receipt TEXT)')
        os.chmod(self.path,0o600)

    def connect(self):return sqlite3.connect(self.path,timeout=10)

    def prepare(self,queue,data,filename,kind='document',options_value=None):
        queue=require_queue(queue)
        if not isinstance(data,bytes) or not 0<len(data)<=MAX_INPUT_BYTES:raise ValueError('Input must be 1 byte–3 MiB')
        if not isinstance(filename,str) or len(filename)>200 or any(ord(c)<32 for c in filename):raise ValueError('Invalid print title')
        profile=profiles().get(queue,{'kind':'document'})
        selected_options=print_options(options_value)
        if kind=='document':
            if profile.get('kind')=='escpos':raise ValueError('Use receipt text/image with this ESC/POS queue; PDF is not printer command data')
            suffix=Path(filename).suffix.casefold()
            if suffix not in {'.txt','.pdf','.png','.jpg','.jpeg'}:raise ValueError('Print PDF, UTF-8 text, PNG or JPEG; export DOCX/EPUB/Mercury manuscripts to PDF first')
            if suffix=='.pdf' and not data.startswith(b'%PDF-'):raise ValueError('Invalid PDF header')
            if suffix=='.txt':data.decode('utf-8')
            payload=data
        elif kind in {'receipt-text','receipt-image'}:
            if profile.get('kind')!='escpos':raise ValueError('Configure this verified receipt queue with profile --kind escpos first')
            if set(selected_options)!={'copies'}:raise ValueError('Receipt jobs do not support document page/media/sides options')
            payload=b'\x1b@'+(receipt_text(data.decode('utf-8'),profile['columns']) if kind=='receipt-text' else receipt_image(data,profile['width']))
        else:raise ValueError('Unsupported print kind')
        ident=uuid.uuid4().hex
        meta={'id':ident,'queue':queue,'title':filename,'kind':kind,'options':selected_options,'profile':profile,'bytes':len(payload),'sha256':hashlib.sha256(payload).hexdigest(),'state':'prepared','expires_in_seconds':PLAN_LIFETIME,'note':'Not sent. Review printer/options and use lk print send ID --confirm. Spooler acceptance does not prove physical printing.'}
        if kind=='receipt-text' or kind=='document' and Path(filename).suffix.casefold()=='.txt':
            meta['text_preview']=data.decode('utf-8')[:2000];meta['preview_truncated']=len(data.decode('utf-8'))>2000
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            pending=db.execute('SELECT COALESCE(SUM(length(payload)),0) FROM jobs').fetchone()[0]
            if pending+len(payload)>MAX_PENDING_BYTES:raise ValueError('Print spool is full; discard old plans before preparing more')
            db.execute('INSERT INTO jobs VALUES (?,?,?,?,?,?)',(ident,time.time(),'prepared',json.dumps(meta),payload,'{}'))
        return meta

    def get(self,ident):
        if not isinstance(ident,str) or not re.fullmatch(r'[0-9a-f]{32}',ident):raise ValueError('Invalid print plan ID')
        with self.connect() as db:row=db.execute('SELECT created,state,meta,payload,receipt FROM jobs WHERE id=?',(ident,)).fetchone()
        if not row:raise ValueError('Print plan not found on this owner')
        return row

    def inspect(self,ident):
        created,state,meta,_,receipt=self.get(ident)
        value=dict(json.loads(meta),state=state,created=created,receipt=json.loads(receipt))
        if state!='prepared':value['note']='State: '+state+'. Check the receipt and CUPS jobs; this plan cannot be sent again.'
        return value

    def discard(self,ident,confirm=False):
        row=self.get(ident);meta=json.loads(row[2]);meta.pop('text_preview',None);meta.pop('preview_truncated',None)
        if confirm is not True:return self.inspect(ident)
        with self.connect() as db:
            cursor=db.execute("UPDATE jobs SET payload=NULL,meta=?,state='discarded' WHERE id=? AND state='prepared'",(json.dumps(meta),ident))
            if not cursor.rowcount:raise ValueError('Only an unsent prepared plan can be discarded')
        return self.inspect(ident)

    def send(self,ident,confirm=False):
        created,state,raw,payload,_=self.get(ident);meta=json.loads(raw)
        if confirm is not True:return self.inspect(ident)
        if state!='prepared':return self.inspect(ident)
        if time.time()-created>PLAN_LIFETIME:raise ValueError('Plan expired; prepare again to review current settings')
        require_queue(meta['queue'])
        if profiles().get(meta['queue'],{'kind':'document'})!=meta['profile']:raise ValueError('Printer profile changed; prepare a fresh plan')
        if hashlib.sha256(payload).hexdigest()!=meta['sha256']:raise ValueError('Print payload changed')
        args=['lp','-d',meta['queue'],'-n',str(meta['options']['copies']),'-t',meta['title']]
        for key,option in [('pages','page-ranges'),('media','media'),('sides','sides')]:
            if key in meta['options']:args+=['-o',option+'='+meta['options'][key]]
        if meta['kind'].startswith('receipt-'):args+=['-o','raw']
        args+=['--','-']
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            cursor=db.execute("UPDATE jobs SET state='submitting' WHERE id=? AND state='prepared'",(ident,))
            if not cursor.rowcount:return self.inspect(ident)
        try:
            output=run(args,payload)
            match=re.search(r'request id is ('+re.escape(meta['queue'])+r'-[0-9]+)\b',output)
            state='queued' if match else 'uncertain'
            receipt={'job':match[1] if match else None,'output':output,'note':'Accepted by CUPS; physical delivery is not verified.' if match else 'No job ID verified. Check lk print jobs; do not resend automatically.'}
        except (OSError,RuntimeError,subprocess.SubprocessError) as error:
            state='uncertain';receipt={'error':str(error),'note':'Submission may have reached CUPS. Inspect jobs; this plan will not be resent.'}
        meta.pop('text_preview',None);meta.pop('preview_truncated',None)
        with self.connect() as db:db.execute('UPDATE jobs SET state=?,receipt=?,meta=?,payload=NULL WHERE id=?',(state,json.dumps(receipt),json.dumps(meta),ident))
        return self.inspect(ident)


def local(payload=None):
    value=dict(payload or {});action=value.pop('action','list')
    if action=='completion':
        import print_completion
        return print_completion.install(**value)
    if action=='list':return catalog()
    if action=='discover':return {'devices':run(['lpinfo','-v']),'note':'Observed device URIs only; nothing configured or printed.'}
    if action=='options':return options(value['queue'])
    if action=='jobs':return jobs(value['queue'])
    if action=='cancel':return cancel(**value)
    if action=='add':return add_queue(**value)
    if action=='profile':return configure_profile(**value)
    if action=='nickname':return nickname(**value)
    if action=='prepare':
        encoded=value.pop('data','')
        if not isinstance(encoded,str) or len(encoded)>4*((MAX_INPUT_BYTES+2)//3):raise ValueError('Print input exceeds 3 MiB')
        data=base64.b64decode(encoded,validate=True)
        return Spool().prepare(data=data,**value)
    if action=='inspect':return Spool().inspect(value['ident'])
    if action=='send':return Spool().send(**value)
    if action=='discard':return Spool().discard(**value)
    raise ValueError('Unknown print operation')
