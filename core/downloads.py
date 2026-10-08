"""Durable yt-dlp jobs on the owning node, with explicitly opted-in retention."""
from __future__ import annotations
import json, os, shutil, subprocess, threading, time, uuid
from pathlib import Path
from urllib.parse import urlparse


def binary(name):
    found=shutil.which(name)
    if found: return found
    for base in ('/opt/homebrew/bin','/usr/local/bin','/home/linuxbrew/.linuxbrew/bin','/usr/bin'):
        candidate=Path(base)/name
        if candidate.is_file() and os.access(candidate,os.X_OK): return str(candidate)
    raise RuntimeError(f'{name} is missing on this node; rerun ./install.sh')


def youtube_url(value):
    url=str(value).strip(); parsed=urlparse(url)
    if parsed.scheme not in {'http','https'} or parsed.hostname not in {'youtube.com','www.youtube.com','m.youtube.com','music.youtube.com','youtu.be'} or parsed.username or parsed.password:
        raise ValueError('Supply a YouTube video URL; use lk ytd find QUERY to choose a video')
    if parsed.port not in {None,80,443}: raise ValueError('Unsupported URL port')
    return url


class Downloads:
    def __init__(self,state=None,index=None,forget=None):
        self.state=Path(state or Path.home()/'.local/share/future-crash-look/downloads')
        self.state.mkdir(parents=True,exist_ok=True)
        self.index=index or (lambda row:None); self.forget=forget or (lambda paths:None)
        self.lock=threading.RLock(); self.slots=threading.Semaphore(2); self.processes={}
        for row in self.list():
            if row['stage'] not in {'complete','failed','cancelled','expired'}:
                self.update(row['id'],stage='failed',error='Node restarted before download confirmation; retry explicitly')

    def path(self,job):
        if len(str(job))!=32 or any(c not in '0123456789abcdef' for c in str(job)): raise ValueError('Invalid download job id')
        return self.state/(job+'.json')

    def get(self,job):
        with self.lock:
            try: return json.loads(self.path(job).read_text())
            except FileNotFoundError: raise ValueError('Download job not found')

    def update(self,job,**fields):
        with self.lock:
            path=self.path(job)
            row=json.loads(path.read_text()) if path.exists() else {'id':job,'created':time.time()}
            row.update(fields,updated=time.time())
            temp=path.with_suffix('.tmp'); temp.write_text(json.dumps(row,ensure_ascii=False)); os.chmod(temp,0o600); temp.replace(path)
            return row

    def list(self):
        with self.lock:
            rows=[]
            for path in self.state.glob('*.json'):
                try: rows.append(json.loads(path.read_text()))
                except (OSError,ValueError): continue
            return sorted(rows,key=lambda row:row.get('created',0),reverse=True)

    def create(self,url,directory=None,holding=False):
        url=youtube_url(url); binary('yt-dlp'); binary('ffmpeg')
        with self.lock:
            if sum(row['stage'] not in {'complete','failed','cancelled','expired'} for row in self.list())>=8:
                raise RuntimeError('Download queue is full')
            job=uuid.uuid4().hex
            root=Path(directory).expanduser().resolve() if directory else Path.home()/'Downloads'/('LOOK-Holding' if holding else 'LOOK')
            row=self.update(job,url=url,root=str(root),holding=bool(holding),expires_at=None,stage='queued',indexed=False,progress={})
            threading.Thread(target=self.run,args=(job,),daemon=True).start()
            return row

    def run(self,job):
        stage=None
        with self.slots:
            try:
                if self.get(job)['stage']=='cancelled': return
                row=self.update(job,stage='resolving'); root=Path(row['root']); root.mkdir(parents=True,exist_ok=True)
                stage=root/('.look-ytd-stage-'+job); stage.mkdir()
                argv=[binary('yt-dlp'),'--ignore-config','--no-playlist','--no-simulate','--no-overwrites','--newline','--no-colors',
                      '--progress','--write-info-json','--ffmpeg-location',binary('ffmpeg'),
                      '-f','bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/b','--merge-output-format','mp4','-S','vcodec:h264,acodec:aac',
                      '-P',str(stage),'-o','%(title).180B [%(id)s].%(ext)s',
                      '--progress-template','download:LOOK_PROGRESS:%(progress)j',
                      '--print','after_move:LOOK_FILE:%(filepath)j','--',row['url']]
                with self.lock:
                    if self.get(job)['stage']=='cancelled': return
                    proc=subprocess.Popen(argv,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,bufsize=1)
                    self.processes[job]=proc
                final=None; messages=[]
                for line in proc.stdout:
                    line=line.strip()
                    if line.startswith('LOOK_PROGRESS:'):
                        try:
                            progress=json.loads(line.split(':',1)[1]); fields={key:progress.get(key) for key in ('downloaded_bytes','total_bytes','total_bytes_estimate','speed','eta','status')}
                            with self.lock:
                                if self.get(job)['stage']!='cancelled':
                                    self.update(job,stage='processing' if fields['status']=='finished' else 'downloading',progress=fields)
                        except ValueError: pass
                    elif line.startswith('LOOK_FILE:'):
                        final=Path(json.loads(line.split(':',1)[1])).resolve()
                    else:
                        messages=(messages+[line[-600:]])[-8:]
                proc.stdout.close()
                code=proc.wait()
                if self.get(job)['stage']=='cancelled': return
                if code or not final or not final.is_file(): raise RuntimeError('\n'.join(messages) or f'yt-dlp failed with exit {code}')
                if not final.is_relative_to(stage.resolve()): raise RuntimeError('Download escaped its staging directory')
                info_files=list(stage.glob('*.info.json')); metadata={}
                if info_files:
                    if info_files[0].stat().st_size>16*1024*1024: raise ValueError('Video metadata exceeds 16 MB')
                    metadata=json.loads(info_files[0].read_text())
                facts={key:metadata.get(key) for key in ('id','title','description','channel','uploader','tags','upload_date','webpage_url')}
                # Keep only completed media and descriptive metadata; fragments
                # and other temporary files are never published or cataloged.
                owned=[final,*info_files]
                for path in list(stage.iterdir()):
                    if path not in owned:
                        if path.is_dir(): shutil.rmtree(path)
                        else: path.unlink()
                with self.lock:
                    if self.get(job)['stage']=='cancelled': return
                    destination=root/job
                    if destination.exists(): raise FileExistsError(destination)
                    self.update(job,stage='publishing'); stage.rename(destination); stage=None
                    files=[destination/path.name for path in owned]
                    manifest=[{'path':str(path),'bytes':path.stat().st_size,'mtime':path.stat().st_mtime} for path in files]
                    row=self.update(job,stage='indexing',directory=str(destination),file=str(destination/final.name),files=manifest,metadata=facts,
                                    expires_at=time.time()+30*86400 if row['holding'] else None)
                try:
                    self.index(row); self.update(job,stage='complete',indexed=True,catalog_state='locally indexed; available to live Fabric queries')
                except Exception as exc:
                    self.update(job,stage='complete',indexed=False,catalog_state='indexing failed; use lk ytd index JOB',index_error=str(exc))
            except Exception as exc:
                if self.get(job).get('stage')!='cancelled': self.update(job,stage='failed',error=str(exc))
            finally:
                with self.lock: self.processes.pop(job,None)
                if stage and stage.exists(): shutil.rmtree(stage)

    def cancel(self,job):
        with self.lock:
            row=self.get(job)
            if row['stage'] in {'complete','expired','failed','publishing','indexing'}: raise ValueError('Download is no longer active')
            row=self.update(job,stage='cancelled')
            proc=self.processes.get(job)
            if proc:
                proc.terminate()
                def force_stop():
                    if proc.poll() is None: proc.kill()
                timer=threading.Timer(3.0,force_stop); timer.daemon=True; timer.start()
            return row

    def reindex(self,job):
        row=self.get(job)
        if row['stage']!='complete': raise ValueError('Only completed downloads can be indexed')
        self.index(row); return self.update(job,indexed=True,index_error='',catalog_state='locally indexed; available to live Fabric queries')

    def keep(self,job,directory=None):
        with self.lock:
            row=self.get(job)
            if row['stage']!='complete': raise ValueError('Only completed downloads can be kept')
            if not row['holding']: return row
            # Remove expiration before moving so a failed move retains the item.
            self.update(job,expires_at=None)
            source=Path(row['directory']); target=Path(directory).expanduser().resolve() if directory else Path.home()/'Downloads'/'LOOK'
            target.mkdir(parents=True,exist_ok=True); target=target/job
            if target.exists(): raise FileExistsError(target)
            shutil.move(str(source),str(target))
            oldpaths=[item['path'] for item in row['files']]
            files=[dict(item,path=str(target/Path(item['path']).name)) for item in row['files']]
            row=self.update(job,indexed=False,holding=False,expires_at=None,directory=str(target),file=str(target/Path(row['file']).name),files=files)
            try:
                self.forget(oldpaths); self.index(row)
                return self.update(job,indexed=True,index_error='',catalog_state='locally indexed; available to live Fabric queries')
            except Exception as exc:
                return self.update(job,indexed=False,index_error=str(exc),catalog_state='indexing failed; use lk ytd index JOB')

    def expire(self,stamp=None):
        stamp=time.time() if stamp is None else stamp
        with self.lock:
            for row in self.list():
                if row['stage']!='complete' or not row.get('holding') or not row.get('expires_at') or row['expires_at']>stamp: continue
                folder=Path(row['directory']); paths=[Path(item['path']) for item in row['files']]
                try:
                    unchanged=not folder.is_symlink() and set(folder.iterdir())==set(paths)
                    for item,path in zip(row['files'],paths):
                        unchanged=unchanged and path.resolve().parent==folder and not path.is_symlink() and path.stat().st_size==item['bytes'] and path.stat().st_mtime==item['mtime']
                    if not unchanged:
                        self.update(row['id'],expires_at=None,retention='changed files retained for review'); continue
                    for path in paths: path.unlink()
                    folder.rmdir(); self.forget([str(path) for path in paths]); self.update(row['id'],stage='expired',indexed=False)
                except OSError as exc: self.update(row['id'],retention_error=str(exc))

    def maintenance(self):
        while True:
            self.expire(); time.sleep(3600)

    def search(self,query):
        query=str(query).strip()
        if not query or len(query)>300: raise ValueError('A bounded search query is required')
        run=subprocess.run([binary('yt-dlp'),'--ignore-config','--flat-playlist','--dump-single-json','--skip-download','--',f'ytsearch5:{query}'],capture_output=True,text=True,timeout=45)
        if run.returncode: raise RuntimeError(run.stderr[-1200:])
        data=json.loads(run.stdout)
        return [{'title':entry.get('title'),'url':'https://www.youtube.com/watch?v='+str(entry['id']),'channel':entry.get('channel'),'duration':entry.get('duration')} for entry in data.get('entries') or [] if entry and entry.get('id')][:5]
