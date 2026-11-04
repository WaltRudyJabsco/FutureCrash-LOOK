"""Terminal museum browsing; remote work never runs in the input loop."""
import argparse
import concurrent.futures
import hashlib
import json
from pathlib import Path
import os
import re
import threading
import shutil
import sys
import termios
import time
import tty
import urllib.request
import urllib.parse
import urllib.error
import book_reader
import terminal_style
import museum_art
from look_renderer import NativePreviewController

BASE='http://127.0.0.1:7332'
MAX_IMAGE_BYTES=20*1024*1024
SLIDE_SECONDS=10

def adjacent_artwork(items,index,step):
    """Cycle within the visible collection, skipping works not downloaded yet."""
    for offset in range(1,len(items)+1):
        candidate=(index+step*offset)%len(items)
        if items[candidate].get('downloaded'):return candidate
    return index

def preference(value=None):
    path=Path.home()/'.config/look/museum.json'
    if value:book_reader.write_json(path,{'node':value})
    try:return json.loads(path.read_text()).get('node') or 'local'
    except (OSError,ValueError):return 'local'

class Background:
    """Read-only preview/search waits must not keep a closed desk alive."""
    def submit(self,fn,*args,**kwargs):
        future=concurrent.futures.Future()
        def run():
            try:future.set_result(fn(*args,**kwargs))
            except Exception as exc:future.set_exception(exc)
        threading.Thread(target=run,daemon=True).start();return future
    def shutdown(self,**kwargs):pass

class Client:
    def __init__(self,node):self.node=node
    def request(self,action=None,*,suffix='',**fields):
        query={'target':self.node}
        if action:payload=json.dumps(dict(fields,action=action)).encode()
        else:query.update(fields);payload=None
        req=urllib.request.Request(BASE+'/v1/museum'+suffix+'?'+urllib.parse.urlencode(query),data=payload,headers={'Content-Type':'application/json'})
        try:
            with urllib.request.urlopen(req,timeout=90) as response:result=json.load(response)
        except urllib.error.HTTPError as exc:
            raise ValueError(json.load(exc).get('error','Museum unavailable')) from None
        if not result.get('ok'):raise ValueError(result.get('error','Museum unavailable'))
        return result
    def snapshot(self,query=''):
        try:return self.request(q=query)
        except OSError:
            if self.node!='local':raise
            folder=Path.home()/'.local/share/future-crash-look'
            try:state=json.loads((folder/'museum.json').read_text())
            except FileNotFoundError:return {'items':[],'offline':True}
            rows=[]
            for row in state['items'].values():
                if query.casefold() not in ' '.join(str(v) for v in row.values()).casefold():continue
                rows.append(dict(row,downloaded=(folder/'museum/images'/(row['id']+'.jpg')).is_file()))
            return {'items':rows,'job':state.get('job',{}),'offline':True}
    def image(self,row):
        if not re.fullmatch(r'(met|aic)-[1-9][0-9]{0,9}',str(row.get('id',''))):raise ValueError('Invalid artwork identity')
        if self.node=='local':
            path=Path.home()/'.local/share/future-crash-look/museum/images'/(row['id']+'.jpg')
            if path.is_file():return path
        # Preview images are a cache, not a promise of a pinned collection.
        folder=Path.home()/'.cache/look/museum'/hashlib.sha256(self.node.encode()).hexdigest()[:16];folder.mkdir(parents=True,exist_ok=True)
        path=folder/(row['id']+'.jpg')
        if path.is_file():return path
        url=BASE+'/v1/museum/image?'+urllib.parse.urlencode({'target':self.node,'id':row['id']})
        with urllib.request.urlopen(url,timeout=30) as response:data=response.read(MAX_IMAGE_BYTES+1)
        if len(data)>MAX_IMAGE_BYTES:raise ValueError('Artwork too large')
        temporary=path.with_suffix('.tmp');temporary.write_bytes(data);os.replace(temporary,path);return path


def desk(client,ui):
    fd=sys.stdin.fileno();prior=termios.tcgetattr(fd);pool=Background();native=NativePreviewController()
    items=[];index=0;query='';source='met';page=1;discover=False;message='Loading collection…';future=pool.submit(client.snapshot);preview=None;image_job=None;image_id=None;ascii_mode=not native.enabled;dirty=True;last_size=None;previews={};failed_previews=set();loading_id=None;playing=False;next_slide=0
    def prompt(label):
        native.frame_cleared();termios.tcsetattr(fd,termios.TCSADRAIN,prior)
        try:return input('\n'+label).strip()
        finally:tty.setcbreak(fd)
    try:
        tty.setcbreak(fd);sys.stdout.write('\033[?1049h')
        while True:
            if future and future.done():
                try:
                    result=future.result();items=result.get('items',items);index=min(index,max(0,len(items)-1));message=('Offline · local collection' if result.get('offline') else 'Collection on '+client.node)
                    message+=' · '+str(len(items))+' works'
                    job=result.get('job',{})
                    if job.get('state'):message+=' · starter '+job['state']+' '+str(job.get('saved',0))+'/'+str(job.get('requested',0))+' · '+job.get('theme','')
                except Exception as exc:message=str(exc)
                future=None;dirty=True
            if image_job and image_job.done():
                try:
                    loaded=image_job.result()
                    previews[loading_id]=loaded
                except Exception as exc:message=str(exc);failed_previews.add(loading_id)
                image_job=None;dirty=True
            selected=items[index] if items else None
            if playing and time.monotonic()>=next_slide:
                index=adjacent_artwork(items,index,1);image_id=items[index]['id'];selected=items[index];next_slide=time.monotonic()+SLIDE_SECONDS;dirty=True
            if selected and selected.get('downloaded') and selected['id'] not in previews and selected['id'] not in failed_previews and image_job is None:
                preview=None;loading_id=selected['id'];image_job=pool.submit(client.image,selected)
            preview=previews.get(selected['id']) if selected else None
            size=shutil.get_terminal_size((90,30));width=max(20,size.columns-1);height=size.lines
            if size!=last_size:dirty=True;last_size=size
            if dirty:
                native.frame_cleared()
                art_count=0;thumbnail=None
                lines=['LOOK MUSEUM · '+('Discover '+source if discover else 'Saved collection'),message,'']
                art_rows=max(2,height-13)
                if image_id:
                    row=next((x for x in items if x['id']==image_id),{})
                    lines += [row.get('title','Artwork'),row.get('artist','')+' · '+row.get('date','')]
                    if preview and ascii_mode:
                        try:
                            art=museum_art.colored_symbols(str(preview),width,art_rows);art_count=len(art);lines+=art
                        except Exception:lines+=['Image preview unavailable']
                    else:lines+=['']*art_rows
                    lines += [row.get('museum','')+' · CC0']
                    controls='←/→ previous/next · Space slideshow/pause · i image/ASCII · Esc collection · W shell pane · q quit'
                    lines += [('Playing' if playing else 'Paused')+' · '+str(index+1)+'/'+str(len(items))+' · current list · 10 seconds/work']
                else:
                    page_size=max(1,height-12);start=max(0,index-page_size//2)
                    thumbnail_cols=min(36,width//3) if width>=70 else width
                    list_width=width-thumbnail_cols-3 if width>=70 else width
                    if width<70:page_size=max(1,page_size-7)
                    thumbnail=(4,list_width+3,min(12,page_size),thumbnail_cols) if width>=70 else (4+page_size,1,6,width)
                    for n,row in list(enumerate(items))[start:start+page_size]:lines.append(ui._ansi_clip(('› ' if n==index else '  ')+row['title']+' · '+row.get('artist','')+(' · downloaded' if row.get('downloaded') else ' · online'),list_width))
                    while len(lines)<3+page_size:lines.append('')
                    if width<70:lines+=['']*6
                    if preview and ascii_mode:
                        try:
                            art=museum_art.colored_symbols(str(preview),thumbnail[3],thumbnail[2])
                            for offset,line in enumerate(art):
                                target=thumbnail[0]-1+offset
                                lines[target]=lines[target].ljust(thumbnail[1]-1)+line
                        except Exception:pass
                    if not items:lines+=['No artwork here. d discovers museum art; a downloads a starter pack.']
                    controls='↑↓ select · Enter view · s slideshow · i image/ASCII · d discover · / search · l collection · t source · n/b pages · k keep offline · p pin here · f favorite · a starter · r refresh · W shell pane · q quit'
                footer=terminal_style.command_lines(controls,width)
                lines=lines[:max(1,height-len(footer)-1)]
                clean_lines=[str(line) if (image_id and 5<=n<5+art_count) or (not image_id and thumbnail and ascii_mode and thumbnail[0]-1<=n<thumbnail[0]-1+thumbnail[2]) else re.sub(r'[\x00-\x1f\x7f-\x9f]',' ',str(line)) for n,line in enumerate(lines)]
                rendered=[ui._c(line,'1;34') if n==0 or line.startswith('› ') else line for n,line in enumerate(clean_lines)]
                sys.stdout.write('\033[H'+'\n'.join(ui._ansi_clip(line,width)+'\033[K' for line in rendered+footer)+'\033[J');sys.stdout.flush()
                if preview and not ascii_mode:
                    if image_id:native.request(preview,6,1,art_rows,width)
                    elif thumbnail:native.request(preview,*thumbnail)
                dirty=False
            native.paint_ready()
            key=ui._read_tty_key(fd,.15)
            if key in ('q','Q','\x03'):break
            if not key:continue
            dirty=True
            if key=='W':message=terminal_style.open_pane(Path.cwd());continue
            if image_id:
                if key in ('esc','\x1b'):image_id=None;playing=False;native.frame_cleared()
                elif key in ('i','I'):ascii_mode=not ascii_mode
                elif key in ('left','right','up','down'):
                    index=adjacent_artwork(items,index,-1 if key in ('left','up') else 1);image_id=items[index]['id'];next_slide=time.monotonic()+SLIDE_SECONDS
                elif key in (' ','s','S'):
                    playing=not playing;next_slide=time.monotonic()+SLIDE_SECONDS
                continue
            if key in ('i','I'):ascii_mode=not ascii_mode;continue
            if key in ('up','down','home','end','pageup','pagedown'):
                index=0 if key=='home' else len(items)-1 if key=='end' else max(0,min(len(items)-1,index+{'up':-1,'down':1,'pageup':-10,'pagedown':10}[key]));continue
            if future:continue
            row=items[index] if items else None
            if key in ('enter','\r','\n','s','S') and row:
                if not row.get('downloaded'):message='k keeps this work offline before viewing';continue
                image_id=row['id'];playing=key in ('s','S');next_slide=time.monotonic()+SLIDE_SECONDS
            elif key in ('k','K','p','P','f','F') and row:
                action={'k':'save','p':'pin','f':'favorite'}[key.lower()];future=pool.submit(client.request,action,id=row['id']);discover=False
            elif key in ('a','A'):
                value=prompt('Starter works (1–1000; up to 3 GiB on '+client.node+'; Enter cancels): ')
                if value.isdigit() and 1<=int(value)<=1000:future=pool.submit(client.request,'starter',count=int(value))
            elif key in ('d','D','/','l','L','t','T','n','N','b','B','r','R'):
                if key.lower()=='r':failed_previews.clear()
                if key.lower()=='l':discover=False;query='';page=1
                if key.lower()=='d':discover=True;page=1
                if key.lower()=='t':source='aic' if source=='met' else 'met';discover=True;page=1
                if key in ('d','D','/'):query=prompt('Artist, subject or period: ');page=1
                if key.lower()=='n':page+=1
                if key.lower()=='b':page=max(1,page-1)
                future=pool.submit(client.request,suffix='/search',source=source,q=query or 'landscape',page=page) if discover else pool.submit(client.snapshot,query)
    finally:
        native.frame_cleared();native.close();pool.shutdown(wait=False,cancel_futures=True);termios.tcsetattr(fd,termios.TCSADRAIN,prior);print('\033[?1049l',end='')
    return 0


def main(argv=None,ui=None):
    parser=argparse.ArgumentParser(prog='lk museum',description='An offline art collection from museum open-access sources')
    parser.add_argument('action',nargs='?',default='desk',choices=('desk','list','search','save','pin','sync','starter','status','cancel','slideshow'))
    parser.add_argument('value',nargs='?',default='')
    parser.add_argument('--node',help='Remember the collection owner on this endpoint')
    parser.add_argument('--source',choices=('met','aic'),default='met')
    parser.add_argument('--count',type=int,default=1000);parser.add_argument('--page',type=int,default=1);parser.add_argument('--json',action='store_true')
    args=parser.parse_args(argv);client=Client(preference(args.node))
    try:
        if args.action=='slideshow':
            import saver
            return saver.main(['Museum'],ui=ui,quick=True)
        if args.action=='desk' and sys.stdin.isatty():return desk(client,ui)
        if args.action in ('desk','list','status'):result=client.snapshot(args.value)
        elif args.action=='search':result=client.request(suffix='/search',q=args.value,source=args.source,page=args.page)
        elif args.action in ('save','pin'):result=client.request(args.action,id=args.value)
        elif args.action=='sync':result=client.request('sync')
        elif args.action=='starter':result=client.request('starter',count=args.count)
        else:result=client.request('cancel')
        if args.json:print(json.dumps(result,ensure_ascii=False,indent=2))
        else:
            for row in result.get('items',[]):print(row['id'],row['title'],'·',row.get('artist',''),'·','downloaded' if row.get('downloaded') else 'online')
            if result.get('job'):
                job=result['job'];print('Starter pack:',job.get('state'),str(job.get('saved',0))+'/'+str(job.get('requested',0)),job.get('theme',''))
                for error in job.get('errors',[])[-3:]:print('Source issue:',error)
        return 0
    except (OSError,ValueError) as exc:print('Museum · '+str(exc));return 1
