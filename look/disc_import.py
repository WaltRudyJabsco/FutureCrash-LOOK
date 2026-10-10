"""Owner-local optical import jobs. Fabric transports requests and receipts only."""
from __future__ import annotations
import base64
import csv
import fcntl
import hashlib
import json
import os
from pathlib import Path
import plistlib
import re
import select
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
import uuid

ROOT=Path.home()/'.local/share/look/imports'
LIBRARY=Path.home()/'.local/share/look/media_library.json'
TERMINAL={'complete','failed','cancelled'}
MIN_FREE_BYTES=1024**3


def tool(name):
    found=shutil.which(name)
    if found:return found
    for base in ('/opt/homebrew/bin','/usr/local/bin','/home/linuxbrew/.linuxbrew/bin','/usr/bin','/bin'):
        path=Path(base)/name
        if path.is_file() and os.access(path,os.X_OK):return str(path)
    if name=='makemkvcon':
        path=Path('/Applications/MakeMKV.app/Contents/MacOS/makemkvcon')
        if path.is_file():return str(path)
    return None


def atomic(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    fd,temp=tempfile.mkstemp(dir=path.parent,prefix='.'+path.name)
    try:
        with os.fdopen(fd,'w') as stream:json.dump(value,stream,ensure_ascii=False);stream.flush();os.fsync(stream.fileno())
        os.replace(temp,path)
    finally:
        if os.path.exists(temp):os.unlink(temp)


def query(command,timeout=30):
    result=subprocess.run(command,stdin=subprocess.DEVNULL,capture_output=True,timeout=timeout)
    text=(result.stdout+result.stderr).decode('utf-8','replace')
    if result.returncode:raise ValueError(text.strip()[-1200:] or 'Disc command failed')
    return text


def robot_records(text,prefix):
    for line in text.splitlines():
        if line.startswith(prefix+':'):
            try:yield next(csv.reader([line.partition(':')[2]],escapechar='\\'))
            except (csv.Error,StopIteration):continue


def drives():
    rows=[];warnings=[]
    if sys.platform.startswith('linux'):
        mounts={}
        if tool('lsblk'):
            try:
                data=json.loads(query([tool('lsblk'),'-J','-o','PATH,LABEL,FSTYPE,MOUNTPOINT']))
                def visit(items):
                    for item in items:
                        mounts[item.get('path')]=item;visit(item.get('children') or [])
                visit(data.get('blockdevices') or [])
            except (OSError,ValueError,subprocess.SubprocessError) as exc:warnings.append(str(exc)[:200])
        for path in sorted(Path('/sys/class/block').glob('*')):
            try:
                if (path/'device/type').read_text().strip()!='5':continue
                device='/dev/'+path.name;info=mounts.get(device) or {}
                label=' '.join((path/'device/model').read_text().split())
                rows.append({'id':device,'device':device,'label':label,'disc':info.get('label') or '',
                             'mount':info.get('mountpoint') or ''})
            except OSError:continue
    elif sys.platform=='darwin' and tool('drutil'):
        try:
            listing=query([tool('drutil'),'list'])
            for match in re.finditer(r'^\s*(\d+)\s*[.:]?\s+(.+)$',listing,re.M):
                status=query([tool('drutil'),'-drive',match[1],'status'],5)
                device=re.search(r'(?:Name|Device):\s*(/dev/(?:r)?disk\d+)',status)
                columns=re.split(r'\s{2,}',match[2].strip())
                label=' '.join(columns[:2]) if len(columns)>=4 else match[2].strip()
                row={'id':'drive:'+match[1],'device':device[1] if device else '', 'label':label,'mount':'','disc':''}
                if row['device'] and tool('diskutil'):
                    try:
                        result=subprocess.run([tool('diskutil'),'info','-plist',row['device']],capture_output=True,timeout=30)
                        info=plistlib.loads(result.stdout);row.update(mount=info.get('MountPoint') or '',disc=info.get('VolumeName') or '')
                    except (OSError,ValueError,subprocess.SubprocessError) as exc:warnings.append('Volume discovery: '+str(exc)[:200])
                rows.append(row)
        except (OSError,ValueError,subprocess.SubprocessError) as exc:warnings.append(str(exc)[:200])
    if tool('makemkvcon'):
        try:
            text=query([tool('makemkvcon'),'-r','--noscan','--cache=1','info','disc:9999'],15)
            visible=[fields for fields in robot_records(text,'DRV') if len(fields)>=6 and fields[1]=='1' and fields[2]=='1']
            for fields in visible:
                device=fields[6] if len(fields)>6 else ''
                matches=[row for row in rows if device and row['device']==device]
                if not matches and len(rows)==1 and len(visible)==1:matches=rows
                if matches:
                    matches[0]['makemkv_source']='disc:'+fields[0]
                else:rows.append({'id':'disc:'+fields[0],'device':device,'label':fields[4],'disc':fields[5],'mount':'','makemkv_source':'disc:'+fields[0]})
        except (OSError,ValueError,subprocess.SubprocessError) as exc:warnings.append(str(exc)[:200])
    return {'ok':True,'platform':sys.platform,'drives':rows,'tools':{name:tool(name) for name in
        ('ffmpeg','ffprobe','cd-paranoia','cdparanoia','HandBrakeCLI','makemkvcon')},'warnings':warnings}


def selected_drive(identifier):
    rows=drives()['drives']
    if identifier:rows=[row for row in rows if identifier in {row['id'],row['device']}]
    if len(rows)!=1:raise ValueError('Connect a drive; select --drive explicitly when more than one is available')
    return rows[0]


def toc_from_query(text):
    tracks=[]
    for match in re.finditer(r'^\s*(\d+)\.\s+(\d+)\s+\[[^]]+\]\s+(\d+)\s+\[',text,re.M):
        tracks.append((int(match[1]),int(match[2]),int(match[3])))
    if not tracks:return None
    tracks.sort();first=tracks[0][0];last=tracks[-1][0]
    if first!=1 or last!=len(tracks) or last>99:return None
    leadout=tracks[-1][2]+tracks[-1][1]+150
    offsets=[start+150 for _,_,start in tracks]
    packed=f'{first:02X}{last:02X}{leadout:08X}'+''.join(f'{value:08X}' for value in offsets+[0]*(99-last))
    disc_id=base64.b64encode(hashlib.sha1(packed.encode('ascii')).digest()).decode().translate(str.maketrans('+/=','._-'))
    return {'disc_id':disc_id,'toc':' '.join(map(str,[first,last,leadout,*offsets])),'count':last}


def lookup(toc):
    if not toc:return []
    from urllib.parse import urlencode
    url='https://musicbrainz.org/ws/2/discid/'+toc['disc_id']+'?'+urlencode({'toc':toc['toc'],'inc':'artists+recordings','fmt':'json'})
    request=urllib.request.Request(url,headers={'User-Agent':'FutureCrash-LOOK/8.14.1 (personal disc importer)'})
    try:
        with urllib.request.urlopen(request,timeout=5) as response:data=json.load(response)
    except (OSError,ValueError):return []
    releases=[]
    for release in data.get('releases',[])[:20]:
        artist=''.join(str(item.get('name') or '')+str(item.get('joinphrase') or '') for item in release.get('artist-credit',[]) if isinstance(item,dict))
        for medium in release.get('media',[]):
            tracks=medium.get('tracks') or []
            if len(tracks)!=toc['count']:continue
            releases.append({'title':str(release.get('title') or '')[:200],'artist':artist[:200],
                             'tracks':[str(track.get('title') or (track.get('recording') or {}).get('title') or '')[:200] for track in tracks],
                             'release_id':release.get('id'),'disc':int(medium.get('position') or 1)})
    return releases


def audio_tracks(mount):
    if not mount:return []
    try:
        tracks=[path for path in Path(mount).iterdir() if path.suffix.lower() in {'.aiff','.aif','.aifc'} and path.is_file()]
    except PermissionError as exc:
        raise ValueError('Audio CD access denied by macOS; run lk media import in the terminal on the Mac owning the drive and allow removable-volume access') from exc
    # Finder names start with unpadded track numbers; lexical sorting moves 10 before 2.
    def order(path):
        number=re.match(r'\d+',path.name)
        return (int(number[0]) if number else 1000,path.name.casefold())
    return sorted(tracks,key=order)


def inspect(identifier,kind='cd'):
    if kind not in {'cd','dvd','bluray'}:raise ValueError('Use cd, dvd or bluray')
    drive=selected_drive(identifier)
    if kind=='cd':
        ripper=tool('cd-paranoia') or tool('cdparanoia');toc=None
        if ripper and drive['device']:toc=toc_from_query(query([ripper,'-d',drive['device'],'-Q']))
        native=audio_tracks(drive['mount'])
        if not toc and not native:raise ValueError('Audio CD not readable; insert a CD and check drive permissions / cd-paranoia')
        return {'ok':True,'drive':drive,'engine':'cd-paranoia' if toc else 'macOS audio volume','toc':toc,'releases':lookup(toc),'tracks':len(native) if not toc else toc['count']}
    if drive.get('makemkv_source'):
        text=query([tool('makemkvcon'),'-r','--cache=128','info',drive['makemkv_source']],90)
        titles={}
        for fields in robot_records(text,'TINFO'):
            if len(fields)>=4 and fields[1] in {'2','9','10','16','27'}:
                titles.setdefault(fields[0],{'index':fields[0]})[{'2':'name','9':'duration','10':'bytes','16':'source','27':'filename'}[fields[1]]]=fields[3]
        return {'ok':True,'drive':drive,'engine':'makemkv','titles':list(titles.values())}
    engine=tool('HandBrakeCLI')
    if not engine:raise ValueError('Install HandBrakeCLI or MakeMKV for DVD/Blu-ray imports')
    text=query([engine,'-i',drive['mount'] or drive['device'],'-t','0','--scan'],90)
    titles=[]
    for match in re.finditer(r'\+ title (\d+):(.*?)(?=\+ title \d+:|\Z)',text,re.S):
        duration=re.search(r'duration:\s*([\d:]+)',match[2]);titles.append({'index':match[1],'duration':duration[1] if duration else ''})
    return {'ok':True,'drive':drive,'engine':'handbrake','titles':titles}


def job_path(identifier):
    if not re.fullmatch(r'[a-f0-9]{32}',str(identifier)):raise ValueError('Invalid import job ID')
    return ROOT/'jobs'/(identifier+'.json')


def read_job(identifier):
    row=json.loads(job_path(identifier).read_text())
    row['elapsed_seconds']=round((row.get('finished') or time.time())-row['created'],1)
    percent=row.get('percent')
    if isinstance(percent,(int,float)) and 0<percent<100:
        phase_elapsed=time.time()-row.get('phase_started',row['created'])
        row['estimated_remaining_seconds']=round(phase_elapsed*(100-percent)/percent)
    if row['state'] not in TERMINAL and row.get('pid'):
        try:os.kill(row['pid'],0)
        except ProcessLookupError:
            row.update(state='failed',error='Import worker stopped; partial output retained',finished=time.time());atomic(job_path(identifier),row)
    return row


def list_jobs():
    return sorted([read_job(path.stem) for path in (ROOT/'jobs').glob('*.json')],key=lambda row:row['created'],reverse=True)


def safe_name(value):return re.sub(r'[^\w .()-]+','_',str(value)).strip(' .')[:120] or 'Untitled'


def start(payload):
    kind=payload.get('kind','cd')
    if kind not in {'cd','dvd','bluray'}:raise ValueError('Use cd, dvd or bluray')
    drive=selected_drive(payload.get('drive'))
    if not tool('ffmpeg') or not tool('ffprobe'):raise ValueError('ffmpeg and ffprobe are required')
    if kind!='cd' and not re.fullmatch(r'\d+|all',str(payload.get('title_index',''))):raise ValueError('Scan and choose --title-index for a movie')
    if kind!='cd' and not drive.get('makemkv_source') and not tool('HandBrakeCLI'):raise ValueError('Install MakeMKV or HandBrakeCLI')
    if kind!='cd' and not drive.get('makemkv_source') and payload.get('title_index')=='all':raise ValueError('HandBrake imports one chosen title; all requires MakeMKV')
    metadata=payload.get('metadata') or {}
    if not isinstance(metadata,dict):raise ValueError('Invalid metadata')
    if any(key in metadata and (not isinstance(metadata[key],str) or len(metadata[key])>300) for key in ('title','artist','release_id')):raise ValueError('Invalid release metadata')
    tracks=metadata.get('tracks',[])
    if not isinstance(tracks,list) or len(tracks)>99 or any(not isinstance(value,str) or len(value)>300 for value in tracks):raise ValueError('Invalid track metadata')
    if 'disc' in metadata and (not isinstance(metadata['disc'],int) or not 1<=metadata['disc']<=99):raise ValueError('Invalid disc number')
    title=str(payload.get('title') or metadata.get('title') or drive.get('disc') or ('Audio CD' if kind=='cd' else 'Movie'))[:200]
    destination=Path(payload.get('destination') or Path.home()/('Music' if kind=='cd' else 'Movies')/'Fabric Imports').expanduser().resolve()
    if destination==Path(destination.anchor) or destination==Path.home():raise ValueError('Choose a dedicated import directory')
    destination.mkdir(parents=True,exist_ok=True)
    if shutil.disk_usage(destination).free<MIN_FREE_BYTES:raise ValueError('Less than 1 GiB free at destination')
    ROOT.mkdir(parents=True,exist_ok=True)
    with (ROOT/'submit.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        if any(row['drive']['id']==drive['id'] and row['state'] not in TERMINAL for row in list_jobs()):raise ValueError('This drive already has an import job')
        identifier=uuid.uuid4().hex
        row={'id':identifier,'kind':kind,'drive':drive,'title':title,'metadata':metadata,'title_index':str(payload.get('title_index','')),
             'destination':str(destination),'state':'queued','created':time.time(),'percent':None,'stage':'queued','cancel_requested':False}
        atomic(job_path(identifier),row)
        log=ROOT/'jobs'/(identifier+'.log')
        with log.open('ab') as output:
            try:process=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'worker',identifier],stdin=subprocess.DEVNULL,stdout=output,stderr=output,start_new_session=True)
            except OSError as exc:
                row.update(state='failed',error=str(exc),finished=time.time());atomic(job_path(identifier),row);raise
        row['pid']=process.pid;atomic(job_path(identifier),row)
        threading.Thread(target=process.wait,daemon=True).start()
    return {'ok':True,'job':row}


def cancel(identifier):
    with (ROOT/'submit.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX);row=read_job(identifier)
        if row['state'] not in TERMINAL:row['cancel_requested']=True;atomic(job_path(identifier),row)
    return {'ok':True,'job':row}


def progress(line):
    match=re.search(r'PRGV:(\d+),(\d+),(\d+)',line)
    if match and int(match[3]):return min(100,100*int(match[2])/int(match[3]))
    match=re.search(r'(\d+(?:\.\d+)?)\s*%',line)
    return min(100,float(match[1])) if match else None


def worker(identifier):
    # Submit holds this lock until the worker PID is durably recorded.
    with (ROOT/'submit.lock').open('a') as lock:fcntl.flock(lock,fcntl.LOCK_EX);row=read_job(identifier)
    stage=Path(row['destination'])/('.look-import-'+identifier)
    row.update(state='running',stage='reading',partial_path=str(stage));atomic(job_path(identifier),row)
    def save(**changes):
        with (ROOT/'submit.lock').open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX)
            current=json.loads(job_path(identifier).read_text());row['cancel_requested']=current.get('cancel_requested',False)
            row.update(changes);atomic(job_path(identifier),row)
    def run(command,phase):
        save(stage=phase,percent=None,phase_started=time.time())
        process=subprocess.Popen(command,cwd=stage,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,start_new_session=True)
        buffer=b''
        try:
            while True:
                if json.loads(job_path(identifier).read_text()).get('cancel_requested'):raise InterruptedError('Import cancelled')
                if select.select([process.stdout],[],[],.5)[0]:
                    chunk=os.read(process.stdout.fileno(),8192)
                    if not chunk:break
                    buffer+=chunk
                    parts=re.split(rb'[\r\n]',buffer);buffer=parts.pop()
                    for part in parts:
                        line=part.decode('utf-8','replace');print(line,flush=True)
                        if progress(line) is not None:save(percent=progress(line))
                    buffer=buffer[-65536:]
                elif process.poll() is not None:break
            if process.wait():raise ValueError('Import tool failed; see '+str(ROOT/'jobs'/(identifier+'.log')))
        finally:
            if process.poll() is None:
                os.killpg(process.pid,signal.SIGTERM)
                try:process.wait(timeout=3)
                except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL);process.wait()
            process.stdout.close()
    try:
        stage.mkdir()
        drive=row['drive'];metadata=row['metadata'];outputs=[]
        if row['kind']=='cd':
            ripper=tool('cd-paranoia') or tool('cdparanoia')
            if ripper and drive['device']:
                run([ripper,'-d',drive['device'],'-B'],'reading audio CD')
                inputs=sorted(stage.glob('*.wav'))
            else:
                inputs=audio_tracks(drive['mount'])
            if not inputs:raise ValueError('No audio tracks read; insert an audio CD and check access to the drive')
            expected=metadata.get('tracks') or []
            for number,path in enumerate(inputs,1):
                title=expected[number-1] if number<=len(expected) else path.stem
                output=stage/(f'{number:02d} - '+safe_name(title)+'.flac')
                tags={'title':title,'artist':str(metadata.get('artist') or 'Unknown artist'),'album_artist':str(metadata.get('artist') or 'Unknown artist'),'album':row['title'],'track':str(number),'disc':str(metadata.get('disc') or 1)}
                command=[tool('ffmpeg'),'-nostdin','-v','error','-n','-i',str(path),'-c:a','flac']
                for key,value in tags.items():command+=['-metadata',key+'='+value]
                run([*command,str(output)],f'encoding track {number}/{len(inputs)}')
                atomic(output.with_suffix('.info.json'),tags);outputs.append(output)
        elif drive.get('makemkv_source'):
            run([tool('makemkvcon'),'-r','--progress=-same','--cache=512','mkv',drive['makemkv_source'],row['title_index'],str(stage)],'reading movie')
            outputs=sorted(stage.glob('*.mkv'))
        else:
            output=stage/(safe_name(row['title'])+'.mp4')
            run([tool('HandBrakeCLI'),'-i',drive['mount'] or drive['device'],'-t',row['title_index'],'-o',str(output),'-e','x264','-q','20','-B','160'],'encoding movie')
            outputs=[output]
        if not outputs:raise ValueError('No media produced; partial files retained')
        if row['kind']!='cd':
            for path in outputs:
                atomic(path.with_suffix('.info.json'),{'title':row['title'] if len(outputs)==1 else row['title']+' · '+path.stem,
                    'description':'Imported from '+drive.get('label','optical disc')})
        for path in outputs:
            if not path.is_file() or path.stat().st_size==0:raise ValueError('Empty import output')
            save(stage='verifying media')
            probe=json.loads(query([tool('ffprobe'),'-v','error','-show_entries','format=duration:stream=codec_type','-of','json',str(path)]))
            expected='audio' if row['kind']=='cd' else 'video'
            if not any(stream.get('codec_type')==expected for stream in probe.get('streams',[])) or float((probe.get('format') or {}).get('duration') or 0)<=0:
                raise ValueError('Output has no valid '+expected+' stream/duration')
        # Publish the whole verified directory at once; unfinished output stays hidden.
        if row['kind']=='cd':
            for path in stage.glob('*.wav'):path.unlink()
        final=Path(row['destination'])/(safe_name(row['title'])+' - '+identifier[:8])
        atomic(stage/'import.json',{'job':identifier,'kind':row['kind'],'drive':drive,'metadata':metadata,
                                  'title_index':row['title_index'],'files':[path.name for path in outputs],'created':row['created']})
        save(stage='publishing')
        if row['cancel_requested']:raise InterruptedError('Import cancelled')
        stage.rename(final)
        save(stage='cataloging',output=str(final),partial_path=None)
        try:from . import media_core
        except ImportError:import media_core
        media_core.update_library(LIBRARY,lambda current:media_core.scan_root(final,current))
        try:from . import managed_folders
        except ImportError:import managed_folders
        managed_folders.register(final)
        save(state='complete',stage='complete',percent=100,finished=time.time(),output=str(final),partial_path=None)
    except Exception as exc:
        save(state='cancelled' if isinstance(exc,InterruptedError) else 'failed',error=str(exc)[:1000],finished=time.time())


def request(action,payload=None):
    payload=payload or {}
    if action=='drives':return drives()
    if action=='scan':return inspect(payload.get('drive'),payload.get('kind','cd'))
    if action=='start':return start(payload)
    if action=='jobs':return {'ok':True,'jobs':list_jobs()}
    if action=='status':return {'ok':True,'job':read_job(payload.get('id'))}
    if action=='cancel':return cancel(payload.get('id'))
    raise ValueError('Unknown disc import action')


if __name__=='__main__':
    if len(sys.argv)==3 and sys.argv[1]=='worker':worker(sys.argv[2])
    else:raise SystemExit('Use lk media import --help')
