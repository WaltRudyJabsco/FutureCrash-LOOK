"""Terminal museum browsing; remote work never runs in the input loop."""
import argparse
import concurrent.futures
import hashlib
import json
from pathlib import Path
import os
import re
import threading
import textwrap
import random
import museum_library
import unicodedata
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
LIST_CONTROLS='1 To explore · 2 Discover · 3 Collections · 4 Favorites · 5 Removal review · 6 All works · x mark/undo removal · u keep view here · o offline only · c new collection · m add/remove · ↑↓ select · Shift+↑↓ page · Shift+←→ top/end · F sort · Enter view · s slideshow · i image/ASCII · d discover · / search · l library · t source · n/b pages · K save to owner · k keep here · f thumbs up/favorite · a build starter library · h museum highlights · j daily refill · r refresh · p print · W shell pane · q quit'

def adjacent_artwork(items,index,step):
    """Cycle within the visible collection, skipping works not downloaded yet."""
    for offset in range(1,len(items)+1):
        candidate=(index+step*offset)%len(items)
        if items[candidate].get('downloaded'):return candidate
    return index

SORTS=('Title','Artist','Century','Museum','Shuffle')
SHIFT_KEYS={'shiftup':'pageup','shiftdown':'pagedown','shiftleft':'home','shiftright':'end'}

def artwork_year(row):
    date=row.get('date','')
    century=re.search(r'(\d{1,2})(?:st|nd|rd|th) century',date,re.I)
    year=re.search(r'(?<!\d)(\d{3,4})(?!\d)',date)
    value=(int(century[1])-1)*100 if century else int(year[1]) if year else None
    if value is not None and re.search(r'B\.?C\.?',date,re.I):value=-value
    return value

def sorted_artworks(items,mode):
    if mode=='Shuffle':
        rows=list(items);random.shuffle(rows);return rows
    def key(row):
        title=row.get('title','').casefold()
        if mode=='Century':
            year=artwork_year(row)
            return (year is None,year or 0,title)
        field={'Artist':'artist','Museum':'museum'}.get(mode,'title')
        value=row.get(field,'').casefold()
        return (not bool(value),value,title)
    return sorted(items,key=key)

def navigate(index,key,count,page_size):
    key=SHIFT_KEYS.get(key,key)
    if key=='home':return 0
    if key=='end':return max(0,count-1)
    return max(0,min(max(0,count-1),index+{'up':-1,'down':1,'pageup':-page_size,'pagedown':page_size}.get(key,0)))

def artwork_info(row,width):
    lines=[]
    for label,field in [('Title','title'),('Artist','artist'),('Date','date'),('Medium','medium'),('Museum','museum')]:
        value=re.sub(r'[\x00-\x1f\x7f-\x9f]',' ',str(row.get(field) or 'Unknown'))
        lines.extend(textwrap.wrap(label+': '+value,max(8,width))[:2])
    return lines

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
    def change(self,action,**fields):
        changed=self.request(action,**fields)
        result=self.snapshot()
        if changed.get('active_collection'):result['active_collection']=changed['active_collection']
        if action=='sync':result['job']=changed.get('job',{})
        result['notice']='Copy started on this device; library owner stays '+self.node if action=='sync' else 'Kept on this device' if action=='pin' else 'Saved on '+self.node if action=='save' else ''
        return result
    def snapshot(self,query=''):
        try:
            result=self.request()
            if result.get('offline'):return museum_library.snapshot(self.node,query)
            museum_library.remember(self.node,result)
            return museum_library.snapshot(self.node,query,result)
        except (OSError,ValueError):return museum_library.snapshot(self.node,query)
    def image(self,row):
        if not re.fullmatch(r'(met|aic)-[1-9][0-9]{0,9}',str(row.get('id',''))):raise ValueError('Invalid artwork identity')
        cached=museum_library.image(self.node,row['id'])
        if cached:return cached
        if row.get('offline_unavailable'):raise ValueError('Original unavailable offline; reconnect to '+self.node)
        # Preview images are a cache, not a promise of a pinned collection.
        folder=Path.home()/'.cache/look/museum'/hashlib.sha256(self.node.encode()).hexdigest()[:16];folder.mkdir(parents=True,exist_ok=True)
        path=folder/(row['id']+'.jpg')
        if path.is_file():return path
        url=BASE+'/v1/museum/image?'+urllib.parse.urlencode({'target':self.node,'id':row['id']})
        with urllib.request.urlopen(url,timeout=30) as response:data=response.read(MAX_IMAGE_BYTES+1)
        if len(data)>MAX_IMAGE_BYTES:raise ValueError('Artwork too large')
        temporary=path.with_suffix('.tmp');temporary.write_bytes(data);os.replace(temporary,path);return path


def job_progress(job,width=80):
    if not job.get('state'):return ''
    saved=max(0,int(job.get('saved',0)));total=max(1,int(job.get('requested',1)))
    ratio=min(1,saved/total);cells=max(5,min(24,width//4));filled=int(ratio*cells)
    counts=' · '.join(name+': '+str(count) for name,count in job.get('counts',{}).items())
    return '['+'█'*filled+'░'*(cells-filled)+'] '+str(round(ratio*100))+'% · '+str(saved)+'/'+str(total)+' · '+job['state']+(' · '+counts if counts else '')


def desk(client,ui):
    fd=sys.stdin.fileno();prior=termios.tcgetattr(fd);pool=Background();native=NativePreviewController()
    items=[];index=0;query='';source='met';page=1;discover=False;message='Loading collection…';future=pool.submit(client.snapshot);preview=None;image_job=None;image_id=None;ascii_mode=not native.enabled;dirty=True;last_size=None;previews={};failed_previews=set();loading_id=None;playing=False;next_slide=0;sort_mode=0;page_size=10;colors=terminal_style.list_colors();library=[];collections={};view='library';collection_id=None;offline_only=False;offline=False;shuffle_cycle=False
    job={};progress_future=None;next_progress=0
    def prompt(label):
        native.frame_cleared();termios.tcsetattr(fd,termios.TCSADRAIN,prior)
        try:return input('\n'+label).strip()
        finally:tty.setcbreak(fd)
    try:
        tty.setcbreak(fd);sys.stdout.write('\033[?1049h')
        while True:
            if progress_future and progress_future.done():
                try:
                    progress=progress_future.result()
                    if progress.get('offline'):message='Owner offline · progress may be stale'
                    else:
                        job=progress.get('job',{})
                        if job.get('errors'):message='Source issue: '+job['errors'][-1]
                        if job.get('state')!='running' and not discover and future is None:future=pool.submit(client.snapshot,query)
                except Exception as exc:message='Progress unavailable: '+str(exc)
                progress_future=None;dirty=True
            if job.get('state')=='running' and progress_future is None and time.monotonic()>=next_progress:
                progress_future=pool.submit(client.snapshot);next_progress=time.monotonic()+5
            if future and future.done():
                try:
                    prior_id=image_id or (items[index]['id'] if items else None);prior_items=list(items)
                    result=future.result();library=result.get('items',library);collections=result.get('collections',collections);offline=result.get('offline',False)
                    if result.get('active_collection') and not image_id:collection_id=result['active_collection'];view='collections';discover=False
                    items=sorted_artworks(museum_library.view(library,view,collection_id,offline_only),SORTS[sort_mode]);index=min(index,max(0,len(items)-1))
                    if image_id:
                        updated={row['id']:row for row in library};items=[updated.get(row['id'],row) for row in prior_items]
                    index=next((n for n,row in enumerate(items) if row['id']==prior_id),min(index,max(0,len(items)-1)))
                    message=('Owner offline · cached catalog · '+str(result.get('offline_count',0))+' images here' if offline else 'Library owner: '+client.node)
                    message+=' · '+str(len(items))+' works'+(' · Daily refill ON (1000 to explore + favorites)' if result.get('rotation',{}).get('enabled') else '')+(' · '+result['notice'] if result.get('notice') else '')
                    job=result.get('job',{})
                    if job.get('state'):message+=' · job '+job['state']+' '+str(job.get('saved',0))+'/'+str(job.get('requested',0))+' · '+job.get('theme','')
                except Exception as exc:
                    message=str(exc)
                    if discover:items=[]
                future=None;dirty=True
            if image_job and image_job.done():
                try:
                    loaded=image_job.result()
                    previews[loading_id]=loaded
                except Exception as exc:message=str(exc);failed_previews.add(loading_id)
                image_job=None;dirty=True
            selected=items[index] if items else None
            if playing and time.monotonic()>=next_slide:
                previous=index;index=adjacent_artwork(items,index,1)
                if SORTS[sort_mode]=='Shuffle' and index<=previous and len(items)>1:
                    last=items[previous]['id'];items=sorted_artworks(items,'Shuffle')
                    if items[0]['id']==last:items.append(items.pop(0))
                    index=next((n for n,r in enumerate(items) if r.get('downloaded')),0)
                image_id=items[index]['id'];selected=items[index];next_slide=time.monotonic()+SLIDE_SECONDS;dirty=True
            if selected and selected.get('downloaded') and selected['id'] not in previews and selected['id'] not in failed_previews and image_job is None:
                preview=None;loading_id=selected['id'];image_job=pool.submit(client.image,selected)
            preview=previews.get(selected['id']) if selected else None
            size=shutil.get_terminal_size((90,30));width=max(20,size.columns-1);height=size.lines
            if size!=last_size:dirty=True;last_size=size
            if dirty:
                native.frame_cleared()
                art_count=0;thumbnail=None;row_indices={};side_lines={}
                lines=['LOOK MUSEUM · '+('Discover '+source if discover else view.title()+(' / '+collections.get(collection_id,{}).get('name','Choose a collection') if view=='collections' else ''))+' · Sort: '+SORTS[sort_mode],message,job_progress(job,width)]
                art_rows=max(2,height-13)
                if image_id:
                    row=next((x for x in items if x['id']==image_id),{})
                    lines += [row.get('title','Artwork'),row.get('artist','')+' · '+row.get('date','')]
                    if preview and ascii_mode:
                        try:
                            art=museum_art.colored_symbols(str(preview),width,art_rows);art_count=len(art);lines+=art
                        except Exception:lines+=['Image preview unavailable']
                    else:lines+=['']*art_rows
                    lines += [row.get('museum','')+' · CC0'+(' · ★ Favorite' if row.get('favorite') else '')+(' · Removal: '+time.strftime('%b %d %H:%M',time.localtime(row['removal_due'])) if row.get('removal_due') else '')]
                    controls='←/→ previous/next · Space slideshow/pause · F fullscreen · f thumbs up/favorite · k keep here · m collection · x mark/undo removal · i image/ASCII · Esc collection · p print · W shell pane · q quit'
                    lines += [('Playing' if playing else 'Paused')+' · '+str(index+1)+'/'+str(len(items))+' · current list · 10 seconds/work']
                else:
                    page_size=max(1,height-len(terminal_style.command_lines(LIST_CONTROLS,width))-5);start=max(0,min(index-page_size//2,len(items)-page_size))
                    wide=width>=70
                    thumbnail_cols=min(42,width//2) if wide else width
                    list_width=width-thumbnail_cols-3 if wide else width
                    if not wide:page_size=max(1,page_size-10);start=max(0,min(index-page_size//2,len(items)-page_size))
                    thumbnail=(4,list_width+3,max(2,min(10,page_size-8)),thumbnail_cols) if wide else (4+page_size,1,4,width)
                    for n,row in list(enumerate(items))[start:start+page_size]:
                        row_indices[len(lines)]=n
                        lines.append(ui._ansi_clip(('› ' if n==index else '  ')+row['title'],list_width))
                    while len(lines)<3+page_size:lines.append('')
                    if not wide:lines+=['']*10
                    if preview and ascii_mode:
                        try:
                            for offset,line in enumerate(museum_art.colored_symbols(str(preview),thumbnail[3],thumbnail[2])):
                                side_lines[thumbnail[0]-1+offset]=line
                        except Exception:pass
                    if selected:
                        detail_start=thumbnail[0]-1+thumbnail[2]+1
                        for offset,line in enumerate(artwork_info(selected,thumbnail_cols)):
                            target=detail_start+offset
                            if target<len(lines):side_lines[target]=line
                    if not items:lines+=['No artwork here. d discovers museum art; a downloads a build starter library pack.']
                    controls=LIST_CONTROLS
                footer=terminal_style.command_lines(controls,width)
                lines=lines[:max(1,height-len(footer)-1)]
                clean_lines=[str(line) if (image_id and 5<=n<5+art_count) or (not image_id and thumbnail and ascii_mode and thumbnail[0]-1<=n<thumbnail[0]-1+thumbnail[2]) else re.sub(r'[\x00-\x1f\x7f-\x9f]',' ',str(line)) for n,line in enumerate(lines)]
                rendered=[]
                for n,line in enumerate(clean_lines):
                    if n in row_indices:
                        row_number=row_indices[n]
                        line=terminal_style.list_row(line,list_width+1,index=row_number,selected=row_number==index,colors=colors)
                        if row_number!=index and row_number%2:
                            palette=colors['_palette']
                            bg=palette['background'];fg=palette['foreground']
                            rgb=[round(int(bg[i:i+2],16)*.94+int(fg[i:i+2],16)*.06) for i in (1,3,5)]
                            shade='\033[48;2;'+';'.join(map(str,rgb))+'m'
                            plain=re.sub(r'\x1b\[[0-9;]*m','',line)
                            cells=sum(0 if unicodedata.combining(c) else 2 if unicodedata.east_asian_width(c) in {'W','F'} else 1 for c in plain)
                            line=shade+line.removesuffix('\033[0m')+' '*max(0,list_width-cells)+'\033[0m'
                    elif n==0:line=ui._c(line,'1;34')
                    if n in side_lines:
                        # Cursor addressing keeps wide Unicode titles and ANSI styles
                        # from displacing the independent preview/details column.
                        line+='\033['+str(thumbnail[1])+'G'+side_lines[n]
                    rendered.append(line)
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
            if key in ('p','N') and items:
                playing=False
                native.frame_cleared()
                termios.tcsetattr(fd,termios.TCSADRAIN,prior)
                try:
                    import printing
                    path=client.image(items[index])
                    printing.selected_file(path,ui,prefer_receipt=True,default_style="ascii" if ascii_mode else "image",caption=printing.artwork_caption(items[index]))
                    message='Returned from printing'
                except Exception as error:message='Print: '+str(error)
                finally:tty.setcbreak(fd);native.frame_cleared();dirty=True
                continue
            if key in ('f','k','K','x') and items:
                if future:continue
                if offline:message='Reconnect to '+client.node+' to change this work';continue
                row=items[index];playing=False
                future=pool.submit(client.change,{'f':'favorite','k':'pin','K':'save','x':'mark-removal'}[key],id=row['id']);continue
            if (not image_id and key in ('1','2','3','4','5','6','o','c')) or key=='m':
                if future:continue
                if key=='c':
                    if offline:message='Reconnect to '+client.node+' to edit collections';continue
                    name=prompt('New collection name on '+client.node+': ')
                    if name:future=pool.submit(client.change,'collection-create',name=name)
                    continue
                if key in ('3','m'):
                    choices=list(collections)
                    if not choices:message='No named collections. c creates one on '+client.node;view='collections';items=[];continue
                    value=prompt('Collection: '+', '.join(str(n+1)+' '+collections[k]['name'] for n,k in enumerate(choices))+': ')
                    if not value.isdigit() or not 1<=int(value)<=len(choices):continue
                    chosen=choices[int(value)-1]
                    if key=='m':
                        if offline:message='Reconnect to '+client.node+' to edit collections';continue
                        if not items:continue
                        row=items[index]
                        action='collection-remove' if chosen in row.get('collections',[]) else 'collection-add'
                        future=pool.submit(client.change,action,id=row['id'],collection=chosen);continue
                    collection_id=chosen
                if key=='o':offline_only=not offline_only
                else:view={'1':'library','2':'discover','3':'collections','4':'favorites','5':'review','6':'all'}[key];discover=view=='discover'
                image_id=None;index=0
                if discover:future=pool.submit(client.request,suffix='/search',source=source,q=query or 'landscape',page=1)
                else:future=pool.submit(client.snapshot,query)
                continue
            if key=='F' and not image_id:
                selected_id=items[index]['id'] if items else None
                shuffle_cycle=False;sort_mode=(sort_mode+1)%len(SORTS);items=sorted_artworks(items,SORTS[sort_mode])
                index=next((n for n,row in enumerate(items) if row['id']==selected_id),0)
                continue
            key=SHIFT_KEYS.get(key,key)
            if key=='W':message=terminal_style.open_pane(Path.cwd());continue
            if image_id:
                if key=='F':
                    import museum_fullscreen
                    native.frame_cleared();termios.tcsetattr(fd,termios.TCSADRAIN,prior)
                    try:museum_fullscreen.launch(client.node,items,index,playing)
                    except (ValueError,OSError) as exc:message=str(exc)
                    finally:tty.setcbreak(fd)
                    playing=False;future=pool.submit(client.snapshot,query);continue
                if key in ('esc','\x1b'):image_id=None;playing=False;shuffle_cycle=False;native.frame_cleared();future=pool.submit(client.snapshot,query)
                elif key in ('i','I'):ascii_mode=not ascii_mode
                elif key in ('home','end','pageup','pagedown'):
                    available=[row for row in items if row.get('downloaded')]
                    position=next((n for n,row in enumerate(available) if row['id']==image_id),0)
                    if available:
                        image_id=available[navigate(position,key,len(available),page_size)]['id']
                        index=next(n for n,row in enumerate(items) if row['id']==image_id)
                        next_slide=time.monotonic()+SLIDE_SECONDS
                elif key in ('left','right','up','down'):
                    index=adjacent_artwork(items,index,-1 if key in ('left','up') else 1);image_id=items[index]['id'];next_slide=time.monotonic()+SLIDE_SECONDS
                elif key in (' ','s','S'):
                    if not playing and SORTS[sort_mode]=='Shuffle' and not shuffle_cycle:
                        items=items[index:]+items[:index];index=0;shuffle_cycle=True
                    playing=not playing;next_slide=time.monotonic()+SLIDE_SECONDS
                continue
            if key in ('i','I'):ascii_mode=not ascii_mode;continue
            if key in ('up','down','home','end','pageup','pagedown'):
                index=navigate(index,key,len(items),page_size);continue
            if future:continue
            row=items[index] if items else None
            if key in ('enter','\r','\n','s','S') and row:
                if not row.get('downloaded'):message=('Original unavailable offline; reconnect to '+client.node if offline else 'K saves this work to '+client.node+' before viewing');continue
                image_id=row['id'];playing=key in ('s','S');shuffle_cycle=False
                if playing and SORTS[sort_mode]=='Shuffle':items=items[index:]+items[:index];index=0;shuffle_cycle=True
                next_slide=time.monotonic()+SLIDE_SECONDS
            elif key=='u':
                if offline:message='Reconnect to '+client.node+' to copy artwork';continue
                ids=[r['id'] for r in items if r.get('downloaded')]
                if not ids:message='No saved works in this view';continue
                if client.node=='local':message='These works are already on this device';continue
                if prompt('Copy '+str(len(ids))+' works from '+client.node+' to THIS device? Type yes: ').casefold()=='yes':future=pool.submit(client.change,'sync',ids=ids)
            elif key=='j':
                if offline:message='Reconnect to '+client.node+' to configure daily refill';continue
                answer=prompt('Daily refill on '+client.node+': keep about 1000 undecided works plus Favorites, up to 100 new/day. Type on or off: ').lower()
                if answer in ('on','off'):future=pool.submit(client.change,'rotation',enabled=answer=='on')
            elif key=='h':
                if offline:message='Reconnect to '+client.node+' to download highlights';continue
                if prompt('Download up to 500 Met Highlights + 500 Art Institute Featured on '+client.node+'? Existing images reused; 3 GiB budget. Type yes: ').casefold()=='yes':future=pool.submit(client.change,'featured',count=500,source='both')
            elif key in ('a','A'):
                if offline:message='Reconnect to '+client.node+' to build the library';continue
                value=prompt('Build starter library: works (1–1000; downloads up to 3 GiB on '+client.node+'; Enter cancels): ')
                if value.isdigit() and 1<=int(value)<=1000:future=pool.submit(client.change,'starter',count=int(value))
            elif key in ('d','D','/','l','L','t','T','n','N','b','B','r','R'):
                if key.lower()=='r':failed_previews.clear()
                if key.lower()=='l':discover=False;view='library';query='';page=1
                if key.lower()=='d':discover=True;view='discover';page=1
                if key.lower()=='t':source='aic' if source=='met' else 'met';discover=True;view='discover';page=1
                if key in ('d','D','/'):query=prompt('Artist, subject or period: ');page=1
                if key.lower()=='n':page+=1
                if key.lower()=='b':page=max(1,page-1)
                future=pool.submit(client.request,suffix='/search',source=source,q=query or 'landscape',page=page) if discover else pool.submit(client.snapshot,query)
    finally:
        native.frame_cleared();native.close();pool.shutdown(wait=False,cancel_futures=True);termios.tcsetattr(fd,termios.TCSADRAIN,prior);print('\033[?1049l',end='')
    return 0


def main(argv=None,ui=None):
    parser=argparse.ArgumentParser(prog='lk museum',description='An offline art collection from museum open-access sources')
    parser.add_argument('action',nargs='?',default='desk',choices=('desk','list','search','save','pin','sync','starter','featured','rotation','status','cancel','slideshow'))
    parser.add_argument('value',nargs='?',default='')
    parser.add_argument('--node',help='Remember the collection owner on this endpoint')
    parser.add_argument('--source',choices=('met','aic','both'),default=None)
    parser.add_argument('--count',type=int,default=None);parser.add_argument('--page',type=int,default=1);parser.add_argument('--json',action='store_true')
    args=parser.parse_args(argv);client=Client(preference(args.node))
    try:
        if args.action=='slideshow':
            import saver
            return saver.main(['Museum'],ui=ui,quick=True)
        if args.action=='desk' and sys.stdin.isatty():return desk(client,ui)
        if args.action in ('desk','list','status'):result=client.snapshot(args.value)
        elif args.action=='search':result=client.request(suffix='/search',q=args.value,source=args.source or 'met',page=args.page)
        elif args.action in ('save','pin'):result=client.request(args.action,id=args.value)
        elif args.action=='sync':result=client.request('sync')
        elif args.action=='starter':result=client.request('starter',count=args.count if args.count is not None else 1000)
        elif args.action=='rotation':
            if args.value not in ('on','off'):raise ValueError('Use lk museum rotation on or off')
            result=client.request('rotation',enabled=args.value=='on')
        elif args.action=='featured':result=client.request('featured',count=args.count if args.count is not None else 500,source=args.source or 'both')
        else:result=client.request('cancel')
        if args.json:print(json.dumps(result,ensure_ascii=False,indent=2))
        else:
            for row in result.get('items',[]):print(row['id'],row['title'],'·',row.get('artist',''),'·','downloaded' if row.get('downloaded') else 'online')
            if result.get('job'):
                job=result['job'];print('Download:',job.get('state'),str(job.get('saved',0))+'/'+str(job.get('requested',0)),job.get('theme',''))
                if job.get('counts'):print('By museum:',', '.join(name+': '+str(count) for name,count in job['counts'].items()))
                for error in job.get('errors',[])[-3:]:print('Source issue:',error)
        return 0
    except (OSError,ValueError) as exc:print('Museum · '+str(exc));return 1
