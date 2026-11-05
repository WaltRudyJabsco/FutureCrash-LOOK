"""Reviewed Fabric upkeep, with durable per-step receipts and bounded workers."""
from __future__ import annotations
import concurrent.futures,fcntl,io,json,os,platform,re,subprocess,sys,time,urllib.request,uuid,zipfile
from pathlib import Path
try:from . import maintenance,fabric_care
except ImportError:import maintenance,fabric_care
REPOSITORY='WaltRudyJabsco/FutureCrash-LOOK'
MAX_ARCHIVE=128*1024*1024
POLL_SECONDS=2
JOB_TIMEOUT=1800
TERMINAL={'complete','partial','failed'}

def root():return Path.home()/'.local/share/future-crash-look/upkeep'
def read(path,default=None):
    try:return json.loads(Path(path).read_text())
    except FileNotFoundError:return {} if default is None else default

def status(kind='fabric'):
    value=read(root()/(kind+'.json'),{'state':'idle'})
    if value.get('state') in {'queued','running'} and value.get('pid'):
        try:os.kill(value['pid'],0)
        except ProcessLookupError:value=dict(value,state='failed',error='Upkeep worker stopped; run again to resume checks')
        except PermissionError:pass
    return value

def github_latest():
    req=urllib.request.Request('https://api.github.com/repos/'+REPOSITORY+'/commits/main',headers={'Accept':'application/vnd.github+json','User-Agent':'LOOK-Fabric-Upkeep'})
    with urllib.request.urlopen(req,timeout=8) as response:value=json.loads(response.read(1024*1024))
    sha=value.get('sha','')
    if not re.fullmatch('[0-9a-f]{40}',sha):raise ValueError('GitHub returned an invalid commit')
    return {'state':'checked','commit':sha,'repository':REPOSITORY}

def clients():
    try:from . import node
    except ImportError:import node
    def get(target,path):
        if target=='local':return node.http_json('http://127.0.0.1:7332'+path,timeout=60 if path=='/v1/media/fabric' else 15)
        return node._target_get('127.0.0.1',7332,target,path)
    post=lambda target,path,data:node._target_post('127.0.0.1',7332,target,path,data,timeout=40)
    return node,get,post

def plan(source=''):
    if source and not re.fullmatch(r'[A-Za-z0-9_.-]{1,128}',source):raise ValueError('Use a trusted node name')
    node,get,post=clients();snapshot=node.http_json('http://127.0.0.1:7332/v1/nodes',timeout=8)
    report=fabric_care.inspect(snapshot,get)
    try:latest=github_latest()
    except Exception as exc:latest={'state':'unavailable','error':str(exc)}
    report['github']=latest
    if source:
        chosen=next((r for r in report['nodes'] if r['node'].casefold()==source.casefold() or source=='local' and r['node']==report['local']),None)
        if not chosen or not chosen.get('release',{}).get('digest'):raise ValueError('Source must be a reachable trusted node with a registered release')
        report['source']={'kind':'node','node':chosen['node'],**chosen['release']}
    elif latest.get('commit'):
        chosen=next((r for r in report['nodes'] if r.get('release',{}).get('commit')==latest['commit'] and r['release'].get('digest')),None)
        report['source']={'kind':'node','node':chosen['node'],**chosen['release']} if chosen else {'kind':'github',**latest}
    elif report['releases_match']:
        chosen=report['nodes'][0];report['source']={'kind':'node','node':chosen['node'],**chosen['release']}
    else:report['source']={'kind':'unresolved','error':'GitHub unavailable and installed bundles differ; choose run NODE --yes'}
    report['scope']='Registered LOOK runtime; Notes and enabled Mercury sync; Books/Museum/media catalogs; configured essential and Books/Museum backups. Offline-copy policies unchanged.'
    report['receipt']=status();report['review']=uuid.uuid4().hex;report['checked']=time.time()
    root().mkdir(parents=True,exist_ok=True);maintenance.atomic_json(root()/('review-'+report['review']+'.json'),report);return report

def archive_source(relative):
    p=Path(relative);parent=str(p.parent);name=p.name
    if parent=='.local/share/future-crash-look/core':return 'core/'+name
    if parent=='.local/share/future-crash-look':return 'VERSION'
    if parent=='.local/share/look':return 'look/'+name
    if parent=='.local/share/look/docs':return 'look/docs/'+name
    if parent=='.local/share/signal-window':return 'signal-window/'+name
    if parent=='.local/share/albert':return ('signal-window/' if name in {'browser-views.js','fabric.html','fabric-dashboard.js'} else 'albert/')+name
    if parent=='.local/share/future-crash':return 'future-crash/'+name
    if parent=='.local/bin':return ('future-crash/' if name=='future-crash' else 'core/')+name
    raise ValueError('Unknown runtime destination')

def prepare(commit):
    if not re.fullmatch('[0-9a-f]{40}',commit):raise ValueError('Invalid commit')
    req=urllib.request.Request('https://api.github.com/repos/'+REPOSITORY+'/zipball/'+commit,headers={'User-Agent':'LOOK-Fabric-Upkeep'})
    with urllib.request.urlopen(req,timeout=60) as response:raw=response.read(MAX_ARCHIVE+1)
    if len(raw)>MAX_ARCHIVE:raise ValueError('Release archive exceeds limit')
    installed=read(maintenance.registry());paths={f['path']:f['mode'] for f in installed['files']}
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        names=archive.namelist();prefix=names[0].split('/')[0]+'/'
        for name in names:
            relative=name.removeprefix(prefix);p=Path(relative)
            if str(p.parent) in {'core','look'} and p.suffix=='.py':
                dest=('.local/share/future-crash-look/core/' if p.parent.name=='core' else '.local/share/look/')+p.name
                paths.setdefault(dest,0o755 if archive.getinfo(name).external_attr>>16 & 0o111 else 0o644)
        payload={};files=[];total=0
        for dest,mode in sorted(paths.items()):
            info=archive.getinfo(prefix+archive_source(dest));total+=info.file_size
            if total>maintenance.MAX_BUNDLE:raise ValueError('Runtime exceeds size limit')
            if info.external_attr>>16 & 0o170000==0o120000:raise ValueError('Runtime symlinks are not supported')
            data=archive.read(info);payload[dest]=data;files.append({'path':dest,'mode':mode,'size':len(data),'sha256':maintenance.digest(data)})
    manifest={'protocol':maintenance.PROTOCOL,'commit':commit,'release':payload['.local/share/future-crash-look/RELEASE'].decode().strip(),'files':files}
    out=io.BytesIO()
    with zipfile.ZipFile(out,'w') as archive:
        for name,data in [('manifest.json',json.dumps(manifest,sort_keys=True,separators=(',',':')).encode()),*payload.items()]:
            info=zipfile.ZipInfo(name,(1980,1,1,0,0,0));info.create_system=3;info.external_attr=0o600<<16;archive.writestr(info,data)
    data=out.getvalue();digest=maintenance.digest(data);maintenance.validate_bundle(data,digest)
    root().mkdir(parents=True,exist_ok=True);path=root()/(digest+'.zip');path.write_bytes(data)
    return {'digest':digest,'commit':commit}

def prepared(digest):
    if not re.fullmatch('[0-9a-f]{64}',digest):raise ValueError('Invalid prepared digest')
    data=(root()/(digest+'.zip')).read_bytes();maintenance.validate_bundle(data,digest);return data

def start(kind='fabric',source='',review=''):
    if kind not in {'fabric','local'}:raise ValueError('Unknown upkeep job')
    approved=None
    if kind=='fabric':
        if not re.fullmatch('[0-9a-f]{32}',review):raise ValueError('Check the Fabric update plan first')
        approved=read(root()/('review-'+review+'.json'))
        if time.time()-approved.get('checked',0)>3600:raise ValueError('Plan expired; check again')
    root().mkdir(parents=True,exist_ok=True)
    with (root()/(kind+'.lock')).open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        existing=status(kind)
        if existing.get('state') in {'queued','running'}:return existing
        job={'id':uuid.uuid4().hex,'state':'queued','source_request':source,'created':time.time(),'steps':[],'plan':approved}
        path=root()/(kind+'.json');maintenance.atomic_json(path,job)
        argv=[sys.executable,str(Path(__file__).resolve()),'worker',kind,job['id']]
        try:
            if platform.system()=='Linux':
                unit='look-upkeep-'+job['id']
                subprocess.run(['systemd-run','--user','--quiet','--collect','--unit='+unit,'--property=Type=exec',*argv],check=True,capture_output=True,timeout=10)
                job['pid']=int(subprocess.check_output(['systemctl','--user','show',unit,'--property=MainPID','--value'],text=True,timeout=5).strip())
            else:
                with (root()/(kind+'.log')).open('ab') as log:
                    job['pid']=subprocess.Popen(argv,stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True).pid
            maintenance.atomic_json(path,job)
        except Exception as exc:
            job.update(state='failed',error=str(exc));maintenance.atomic_json(path,job);raise
        return job

class ReceiptError(ValueError):
    def __init__(self,receipt):
        self.receipt=receipt
        details=[s['label']+': '+s['state'] for s in receipt.get('steps',[]) if s['state'] not in {'verified','skipped'}]
        super().__init__('; '.join(details) or str(receipt.get('error') or receipt.get('state')))

def wait_for(read_status,accept,timeout=JOB_TIMEOUT):
    deadline=time.monotonic()+timeout;last=None
    while time.monotonic()<deadline:
        try:
            last=read_status()
            if accept(last):return last
            if last.get('state') in {'failed','rolled_back','partial','incomplete'}:raise ReceiptError(last)
        except (OSError,RuntimeError):pass
        time.sleep(POLL_SECONDS)
    raise TimeoutError('No verified completion receipt before timeout: '+str(last))

def worker(kind,identifier):
    path=root()/(kind+'.json')
    with (root()/(kind+'.lock')).open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX);job=read(path)
    if job.get('id')!=identifier:return
    job['state']='running';maintenance.atomic_json(path,job)
    def step(label,fn):
        record={'label':label,'state':'running','started':time.time()};job['steps'].append(record);maintenance.atomic_json(path,job)
        try:
            result=fn();record.update(state='verified',result=result)
            if isinstance(result,dict):
                if result.get('ok') is False or result.get('errors') or result.get('warnings') or result.get('conflicts') or any(r.get('conflicts') or r.get('remote_conflicts') for r in result.get('peers',[])):record['state']='failed'
                if result.get('state') in {'disabled','not running'}:record['state']='skipped'
                if result.get('state')=='not_configured':record['state']='needs_setup'
                if result.get('state') in {'queued','running','staged','sync already running'}:record['state']='pending'
        except Exception as exc:
            record.update(state='failed',error=str(exc))
            if isinstance(exc,ReceiptError):record['result']=exc.receipt
        record['finished']=time.time();maintenance.atomic_json(path,job);return record
    try:
        if kind=='local':local_work(step)
        else:fabric_work(job,step)
        job['state']='complete' if all(s['state'] in {'verified','skipped'} for s in job['steps']) else 'partial'
    except Exception as exc:job.update(state='failed',error=str(exc))
    job['finished']=time.time();maintenance.atomic_json(path,job)
    maintenance.atomic_json(root()/(identifier+'.json'),job)

def local_work(step):
    node,get,post=clients()
    sys.path.insert(0,str(Path.home()/'.local/share/look'))
    def synchronize(path):
        return wait_for(lambda:post('local',path,{}),lambda r:r.get('state')!='sync already running',120)
    step('Notes revision synchronization',lambda:synchronize('/v1/notebook/sync'))
    step('Mercury manuscript synchronization',lambda:synchronize('/v1/mercury/sync'))
    import book_core,books,museum_library,museum_desk
    def scan_books():
        shelf=book_core.Shelf()
        if not shelf.root.is_dir() and not shelf.load()['entries']:return {'state':'disabled','reason':'No local Books folder; shared catalog still refreshed'}
        value=shelf.scan();return {'books':len(value.get('entries',[])),'warnings':value.get('warnings',[])}
    step('Local Books catalog',scan_books)
    def books_catalog():
        result=books.catalog()
        if result.get('warning'):raise ValueError(result['warning'])
        return {'books':len(result.get('entries',[])),'errors':result.get('errors',[])}
    step('Fabric Books catalog cache',books_catalog)
    def museum_catalog():
        owner=museum_desk.preference();value=get(owner,'/v1/museum');museum_library.remember(owner,value)
        return {'owner':owner,'works':len(value.get('items',[]))}
    step('Museum owner catalog cache',museum_catalog)
    def media_catalog():
        value=get('local','/v1/media/fabric');return {'catalog':value.get('count','available'),'errors':value.get('errors',[])}
    step('Media catalog availability',media_catalog)
    backup=fabric_care.backup_status(Path.home())
    if backup.get('configured'):
        def essential():
            recent=[r for r in backup.get('receipts',[]) if r.get('restore_tested') and r.get('node')==backup.get('owner') and 0<=time.time()-r.get('verified_at',0)<fabric_care.BACKUP_MAX_AGE]
            if recent:return {'verified':True,'receipts':recent}
            receipt=fabric_care.start_backup(Path.home())
            if receipt.get('ok') is False:raise ValueError(str(receipt))
            value=wait_for(lambda:fabric_care.backup_status(Path.home())['job'],lambda r:r.get('state')=='complete' and r.get('verified'))
            return value
        step('Essential-state backup and restore check',essential)
    else:
        def shared_backup():
            snapshot=node.http_json('http://127.0.0.1:7332/v1/nodes',timeout=8)
            report=fabric_care.inspect(snapshot,get)
            coverage=next((r.get('backup',{}) for r in report['nodes'] if r['node']==report['local']),{})
            if coverage.get('verified_recently'):return {'verified':True,'verified_at':coverage['verified_at'],'owner':coverage.get('owner'),'scope':'Shared essential-state backup receipt'}
            return {'state':'not_configured','hint':'lk fabric backup add'}
        step('Essential-state backup coverage',shared_backup)
    for name in ('books','museum'):
        helper=Path.home()/'.local/bin'/('fcl-'+name+'-backup')
        if not helper.is_file():
            step(name.title()+' media backup',lambda:{'state':'disabled','reason':'No owner-local media backup integration configured'});continue
        def media_backup(name=name,helper=helper):
            previous=read(Path.home()/'.config/future-crash-look/recovery'/('last-'+name+'-backup.json'))
            if previous.get('restore_tested') and 0<=time.time()-previous.get('verified_at',0)<fabric_care.BACKUP_MAX_AGE:return previous
            started=time.time();subprocess.run([str(helper)],check=True,capture_output=True,timeout=JOB_TIMEOUT)
            receipt=read(Path.home()/'.config/future-crash-look/recovery'/('last-'+name+'-backup.json'))
            if not receipt or not receipt.get('restore_tested'):raise ValueError('No restore-tested media backup receipt')
            if (Path.home()/'.config/future-crash-look/recovery'/('last-'+name+'-backup.json')).stat().st_mtime<started:raise ValueError('Backup receipt was not refreshed')
            return receipt
        step(name.title()+' media backup and restore check',media_backup)

def fabric_work(job,step):
    report=job['plan']
    origin=report['source'];node,get,post=clients();local=report['local']
    if origin['kind']=='unresolved':step('Release source',lambda:(_ for _ in ()).throw(ValueError(origin['error'])))
    else:
        if origin['kind']=='github':
            record=step('Prepare GitHub runtime '+origin['commit'][:7],lambda:prepare(origin['commit']))
            if record['state']!='verified':raise ValueError('Could not prepare release')
            release=record['result'];source=local;staged=True
        else:release=origin;source=origin['node'];staged=False
        # Coordinator updates last; its detached worker survives the node restart.
        for row in sorted(report['nodes'],key=lambda r:r['node']==local):
            name=row['node'];target='local' if name==local else name
            if row.get('errors') and not row.get('release'):
                step(name+' update',lambda:(_ for _ in ()).throw(ValueError('Node offline; retry when connected')));continue
            if row.get('release',{}).get('digest')==release['digest']:continue
            def update(target=target):
                if staged and target=='local':maintenance.schedule('update',data=prepared(release['digest']),expected=release['digest'])
                else:
                    # The target can restart before its acceptance response arrives.
                    # Its digest-specific receipt is the completion authority.
                    try:post(target,'/v1/maintenance/update',{'source':source,'digest':release['digest'],'prepared':staged,'confirm':True})
                    except (OSError,RuntimeError):pass
                result=wait_for(lambda:get(target,'/v1/maintenance/status'),lambda r:r.get('state')=='healthy' and r.get('digest')==release['digest'],420)
                services=get(target,'/v1/services').get('services',{})
                albert=services.get('albert',{})
                if albert.get('managed') and albert.get('state') in {'running','active'}:post(target,'/v1/services/action',{'service':'albert','action':'restart','confirm':True})
                return result
            step(name+' runtime update',update)
    for row in sorted(report['nodes'],key=lambda r:not r.get('backup',{}).get('configured')):
        name=row['node'];target='local' if name==local else name
        def upkeep(target=target):
            accepted=post(target,'/v1/upkeep',{})
            result=wait_for(lambda:get(target,'/v1/upkeep'),lambda r:r.get('id')==accepted['id'] and r.get('state')=='complete')
            return result
        step(name+' libraries and backups',upkeep)
        def health(target=target):
            services=get(target,'/v1/services').get('services',{})
            bad={k:v.get('state') for k,v in services.items() if v.get('managed') and v.get('state') not in {'running','active'}}
            if bad:raise ValueError('Managed services need attention: '+str(bad))
            return {'services':{k:v.get('state') for k,v in services.items()}}
        step(name+' service health',health)

def describe(value):
    if 'source' in value and 'nodes' in value:
        source=value['source'];lines=['Fabric update plan · source '+str(source.get('node') or source.get('kind'))+' · '+str(source.get('commit',''))[:7],value['scope'],'GitHub: '+value['github']['state']]
        lines += [r['node']+': '+('unreachable' if not r.get('release') else str(r['release'].get('commit','unknown'))[:7]) for r in value['nodes']]
        return '\n'.join(lines)
    return '\n'.join(['Fabric update · '+value.get('state','unknown')]+[s['label']+': '+s['state']+(' · '+s['error'] if s.get('error') else '') for s in value.get('steps',[])]+(['Error: '+value['error']] if value.get('error') else []))

def web(handler,base,mutating=False):
    from urllib.parse import urlparse,parse_qs,urlencode
    payload=None;query=parse_qs(urlparse(handler.path).query)
    if mutating:
        if handler.headers.get('Content-Type','').split(';')[0]!='application/json':raise ValueError('JSON required')
        origin=handler.headers.get('Origin')
        if origin and urlparse(origin).netloc!=handler.headers.get('Host'):raise ValueError('Same-origin request required')
        size=int(handler.headers.get('Content-Length') or 0)
        if not 0<size<=2048:raise ValueError('Invalid request size')
        payload=json.loads(handler.rfile.read(size))
        if not isinstance(payload,dict) or payload.get('confirm') is not True:raise ValueError('Confirm the reviewed plan')
        payload={'confirm':True,'review':payload.get('review','')}
    route='/v1/fabric-update'
    if not mutating:route+='?'+urlencode({k:v[0] for k,v in query.items() if k in {'plan','source'}})
    req=urllib.request.Request(base+route,data=json.dumps(payload).encode() if payload else None,headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=150) as response:body=response.read(4*1024*1024)
    handler.send_response(200);handler.send_header('Content-Type','application/json');handler.send_header('Cache-Control','no-store');handler.end_headers();handler.wfile.write(body)

if __name__=='__main__':
    if len(sys.argv)==4 and sys.argv[1]=='worker':worker(sys.argv[2],sys.argv[3])
