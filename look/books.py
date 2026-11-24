"""Terminal bookshelf and public-book acquisition over the existing Fabric transport."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import sys
import subprocess
import tempfile
import termios
import tty
import urllib.parse
import urllib.request

import book_core
import book_reader
import fabric_files
import media_storage
import terminal_style
import look_renderer
import book_preview
from media_ui_work import LatestWork
from notebook_markdown import cell_width
from notebook_markdown import safe_text
from notebook import make_link

BASE='http://127.0.0.1:7332'
DISCOVERY_TIMEOUT_SECONDS=60


def discover(mode='popular',subject='',*,query='',start_index=1):
    """Use the browser's discovery service, including trusted peer caches."""
    if mode=='subjects':return book_core.discover(mode,page=True)
    params=dict(mode=mode,subject=subject,query=query,start_index=start_index)
    try:return fabric_files.request('/v1/books/discover',params,timeout=DISCOVERY_TIMEOUT_SECONDS)
    except OSError:
        # A standalone terminal can still search online without a running node.
        return book_core.discover(mode,subject,query=query,start_index=start_index,page=True)
    except RuntimeError:
        # The service already tried discovery; do not repeat upstream requests.
        return book_core.discover(mode,subject,query=query,start_index=start_index,page=True,cached=True)


def owned_book(row,value):
    ident=book_core.gutenberg_id(row)
    return next((r for r in value.get('entries',[]) if ident and book_core.gutenberg_id(r)==ident),None)


def acquire_book(row,value,owner,*,favorite=False):
    """Called after the UI's download confirmation; never re-download an owned ID."""
    book=owned_book(row,value)
    if book is None:
        response=request('fetch',node=owner,url=row['url'])
        book=dict(response['book'],node=response.get('node') or owner)
    if favorite and not book.get('favorite'):
        request('favorite',node=book.get('node') or owner,id=book['id'],selected=True)
    return book


def request(action=None,node='local',**payload):
    route='/v1/books'+('/fabric' if action is None and node=='all' else '')
    value=fabric_files.request(route,{'target':node} if node!='all' else None,
        json.dumps(dict(payload,action=action)).encode() if action else None,timeout=150 if action=='fetch' else 45 if action=='scan' else 15)
    return value


def catalog():
    cache=Path.home()/'.cache/look/books-fabric.json'
    try:
        value=request(node='all')
        try:
            previous=json.loads(cache.read_text())
            missing={row['node'] for row in value.get('errors',[])}
            value['entries'] += [dict(row,offline=True) for row in previous.get('entries',[]) if row.get('node') in missing]
        except (OSError,ValueError):pass
        cache.parent.mkdir(parents=True,exist_ok=True);media_storage.atomic(cache,value)
        return value
    except (OSError,RuntimeError,ValueError) as exc:
        try:value=json.loads(cache.read_text())
        except (OSError,ValueError):value={'entries':book_core.Shelf().catalog()['entries']}
        return dict(value,warning='Fabric unavailable: '+str(exc))


def rows_for(value,query='',shelf='To explore'):
    groups={}
    for row in value.get('entries',[]):
        key=row['id']
        if key not in groups or (groups[key].get('offline') and not row.get('offline')) or (bool(groups[key].get('offline'))==bool(row.get('offline')) and row.get('reading',{}).get('updated',0)>groups[key].get('reading',{}).get('updated',0)):groups[key]=row
    rows=[r for r in groups.values() if (bool(r.get('removal_due')) if shelf=='Pending removals' else not r.get('removal_due')) and (shelf!='To explore' or not r.get('favorite')) and (shelf!='Favorites' or r.get('favorite')) and (shelf in {'All','To explore','Favorites','Pending removals'} or shelf in {r.get('status'),r.get('shelf')} or shelf in r.get('collections',[]))]
    terms=query.casefold().split()
    return sorted((r for r in rows if all(t in ' '.join(str(r.get(k,'')) for k in ('title','author','shelf','format')).casefold() for t in terms)),key=lambda r:(r.get('author','').casefold(),r.get('title','').casefold()))


def local_copy(row):
    # A remote absolute path can also exist on this computer. Ownership wins.
    node=row.get('node') or 'local'
    if node=='local':return Path(row['path'])
    try:
        identity=fabric_files.request('/v1/identity')['identity']['name']
        if node==identity and Path(row['path']).is_file():return Path(row['path'])
    except (OSError,ValueError,KeyError,RuntimeError):pass
    ident=str(row['id'])
    if len(ident)!=64 or any(c not in '0123456789abcdef' for c in ident):raise ValueError('Invalid book identity')
    suffix=Path(row['path']).suffix.casefold()
    if suffix not in book_core.FORMATS:raise ValueError('Unsupported book format')
    folder=Path.home()/'.cache/look/books';folder.mkdir(parents=True,exist_ok=True);target=folder/(ident+suffix)
    if target.exists() and book_core.digest(target)==ident:return target
    url=BASE+'/v1/books/item?'+urllib.parse.urlencode({'target':node,'id':ident})
    fd,temp=tempfile.mkstemp(dir=folder,prefix='.book-');os.close(fd)
    try:
        with urllib.request.urlopen(url,timeout=30) as response,open(temp,'wb') as stream:
            total=0
            while block:=response.read(65536):
                total+=len(block)
                if total>book_core.MAX_DOWNLOAD_BYTES:raise ValueError('Book transfer exceeds 100 MiB')
                stream.write(block)
        if book_core.digest(temp)!=ident:raise ValueError('Book changed during transfer; refresh and try again')
        os.replace(temp,target)
    finally:Path(temp).unlink(missing_ok=True)
    return target


def import_files(paths,node):
    paths=[Path(p).expanduser().resolve(strict=True) for p in paths]
    for path in paths:book_core.metadata(path)
    if node=='local':
        shelf=book_core.Shelf()
        return [shelf.import_file(path) for path in paths]
    owner=request(node=node)
    fabric_files.copy(paths,f'@{node}:'+owner['root'])
    return request('scan',node=node)['entries']


def read_along(ui,row):
    """Lend the terminal to the existing reader and always restore LO's input."""
    import book_speech
    path=local_copy(row)
    fd=sys.stdin.fileno();old=termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)
        return book_speech.desk(ui,path,row['title'],reading=row.get('reading'),
            save_reading=lambda fields:request('progress',node=row.get('node','local'),id=row['id'],fields=fields))
    finally:
        termios.tcsetattr(fd,termios.TCSADRAIN,old)
        sys.stdout.write('\x1b[0m\x1b[2J\x1b[H');sys.stdout.flush()


def desk(ui,query='',owner=None):
    fd=sys.stdin.fileno();old=termios.tcgetattr(fd);index=0;shelf='To explore';search=False;notice='';results=None
    search_source='library';discovery=None
    owner=owner or media_storage.settings()['node'];sort_reverse=False;help_visible=False;pane_help=False
    previews=LatestWork();native=look_renderer.NativePreviewController();native_images=True;show_preview=True;last_frame=None
    def ask(label,initial='',path=False):
        termios.tcsetattr(fd,termios.TCSADRAIN,old)
        try:
            print('\n'+ui._c(label,'1;36'))
            result,cancelled=look_renderer.prompt_line('› ',initial=initial,picker_root=Path.cwd() if path else None)
            return None if cancelled else result.strip()
        finally:tty.setcbreak(fd)
    def browse(mode,subject='',text='',more=False):
        nonlocal results,index,notice,discovery,search_source,last_frame
        cursor=discovery.get('next_index') if more and discovery else 1
        if not cursor:return
        native.frame_cleared();last_frame=None
        sys.stdout.write('\nSearching Project Gutenberg…');sys.stdout.flush()
        value=discover(mode,subject,query=text,start_index=cursor)
        results=(results or [])+value['entries'] if more else value['entries']
        discovery=dict(mode=mode,subject=subject,text=text,next_index=value.get('next_index'))
        if not more:index=0
        search_source='gutenberg'
        notice=(value.get('warning','')+' · ' if value.get('warning') else '')+'Enter adds to library on '+owner+' · f adds to Favorites'+(' · n more results' if value.get('next_index') else '')
    def select_library(book,*,favorite=False):
        nonlocal value,results,discovery,index,shelf,query,search_source
        value=catalog();results=None;discovery=None;query='';shelf='Favorites' if favorite else 'All';search_source='library'
        rows=rows_for(value,shelf=shelf)
        if sort_reverse:rows=list(reversed(rows))
        index=next((i for i,r in enumerate(rows) if r['id']==book['id']),0)
    try:
        tty.setcbreak(fd)
        # A prior Kitty preview has a graphics placement independent of text.
        # Clear both before any catalog request can delay the first Books frame.
        if os.environ.get('KITTY_WINDOW_ID') or os.environ.get('TERM')=='xterm-kitty':
            sys.stdout.write('\x1b_Ga=d,d=a,q=2\x1b\\')
        sys.stdout.write('\x1b[0m\x1b[2J\x1b[HLOOK BOOKS · opening shelf…');sys.stdout.flush()
        value=catalog()
        while True:
            width,height=ui.shutil.get_terminal_size((100,30));width=max(20,width);height=max(10,height)
            visible=results if results is not None else rows_for(value,query,shelf)
            if sort_reverse:visible=list(reversed(visible))
            index=max(0,min(index,max(0,len(visible)-1)));chosen=visible[index] if visible else None
            owned_gutenberg={book_core.gutenberg_id(r):r for r in value.get('entries',[]) if book_core.gutenberg_id(r)}
            controls='↑↓ move · Shift-arrows page/ends · Enter '+('add/read book' if results is not None else 'read')+' · / search · Tab Library/Gutenberg while searching · g Gutenberg search · d discover · n more results · f favorite · a read aloud · o system reader · s shelves/collections · c new collection · C add/remove collection · x thumbs down/undo · m reading state · e edit · i import · I preview · M image/ASCII · k keep offline · y copy link · R scan/refresh · G reverse · P clipboard · W shell pane · Esc back'
            if width<80 and not help_visible:controls='↑↓ select · Enter add/read · / search · g Gutenberg · d discover · f favorite · n more · W pane · ? help · Esc back'
            else:controls+=' · ? help'
            if pane_help or help_visible:controls+=' · '+' · '.join(terminal_style.pane_shortcuts())
            hints='\n'.join(ui._media_hints(controls,width).splitlines()[:max(1,height-8)]);page=max(1,height-8-len(hints.splitlines()));top=max(0,index-page+1)
            art_width=min(36,width//3) if show_preview and width>=90 else 0
            list_width=width-art_width-3 if art_width else width
            art_height=min(16,page)
            preview=([],None)
            if chosen and art_width:
                key_id=chosen.get('id') or chosen.get('url')
                preview=previews.get((key_id,art_width,art_height),lambda row=dict(chosen),w=art_width,h=art_height:book_preview.preview(row,w,h),([],None),ttl=60) or ([],None)
            art,image=preview
            colors=terminal_style.list_colors();colors=dict(colors)
            # The same palette and selected-row contrast as the media desks.
            title_w=max(12,(list_width-8)*55//100);author_w=max(8,list_width-title_w-21)
            frame=[ui._c('LOOK BOOKS','1;36')+' · '+('PROJECT GUTENBERG' if results is not None else shelf)+f' · {len(visible)} books · import to '+safe_text(owner),
                   ui._c('TITLE'.ljust(title_w)+'  '+'AUTHOR'.ljust(author_w)+'  FORMAT','2')]
            for pos,row in enumerate(visible[top:top+page],top):
                text=ui._media_find_cell(safe_text(('[on shelf] ' if results is not None and book_core.gutenberg_id(row) in owned_gutenberg else '')+row.get('title','')),title_w)+'  '+ui._media_find_cell(safe_text(row.get('author','')),author_w)+'  '+safe_text(row.get('format','EPUB'))
                frame.append(terminal_style.list_row(('› ' if pos==index else '  ')+text,list_width,pos,pos==index,colors))
            frame+=['']*max(0,page-len(visible[top:top+page]))
            if art_width:
                for offset in range(min(page,len(art) or 1)):
                    left=ui._ansi_clip(frame[offset+2],list_width)
                    cells=sum(cell_width(c) for c in ui._strip_ansi(left))
                    right=art[offset] if offset<len(art) else 'Cover unavailable'
                    frame[offset+2]=left+' '*max(0,list_width-cells)+'   '+right
            if chosen:
                detail=' · '.join(str(chosen.get(k) or '') for k in ('status','shelf','position','node'))
                frame.append(ui._c(ui._media_find_cell(safe_text(detail),width),'2'))
            else:frame.append(ui._c('No books here · R scans your configured books folder · i imports a file · g searches Gutenberg','33'))
            if value.get('errors'):frame.append(ui._c('Some owners unavailable · cached books may need an offline copy','33'))
            search_label=('SEARCH '+('Library' if search_source=='library' else 'Gutenberg')+' /' if search else 'FILTER ')
            frame.extend([ui._c(search_label+safe_text(query)+(' · Tab switches source · Enter searches' if search else ''),'1;36'),hints,ui._c(ui._media_find_cell(safe_text(notice),width),'33')])
            rendered=ui._terminal_frame_payload('\n'.join(ui._ansi_clip(line,width) for line in frame))
            if rendered!=last_frame:
                native.frame_cleared();sys.stdout.write(rendered);sys.stdout.flush();last_frame=rendered
            if image and art_width and native_images:native.request(image,3,list_width+4,art_height,art_width)
            native.paint_ready()
            key=ui._read_tty_key(fd,.25)
            if not key:continue
            if key=='\x03':return 0
            if key.startswith('paste:'):
                pasted=safe_text(key[6:])
                query+=(' ' if query and pasted[:1].isspace() else '')+' '.join(pasted.split());search=True;results=[] if search_source=='gutenberg' else None;index=0;continue
            if search:
                if key in {'tab','\t'}:
                    search_source='gutenberg' if search_source=='library' else 'library'
                    if search_source=='library':shelf='All'
                    results=[] if search_source=='gutenberg' else None;index=0;continue
                if key in {'esc','enter','\r','\n'}:
                    search=False
                    if key!='esc' and search_source=='gutenberg':
                        try:browse('search',text=query)
                        except (OSError,ValueError,RuntimeError) as exc:notice=str(exc)
                    continue
                if key in {'\x7f','\b'}:query=query[:-1];index=0;continue
                if len(key)==1 and key.isprintable():query+=key;index=0;continue
                if key not in {'up','down','shiftup','shiftdown','pageup','pagedown','shiftleft','shiftright','home','end'}:continue
            if key=='esc':
                if results is not None:results=None;index=0;continue
                if query:query='';index=0;continue
                return 0
            if key=='?':help_visible=not help_visible;continue
            if key=='/':
                search=True;search_source='gutenberg' if results is not None else 'library'
                if search_source=='library':shelf='All'
                continue
            if key in {'up','down','shiftup','shiftdown','pageup','pagedown','shiftleft','shiftright','home','end'}:
                if key=='up':index-=1
                elif key=='down':index+=1
                elif key in {'shiftup','pageup'}:index-=page
                elif key in {'shiftdown','pagedown'}:index+=page
                elif key in {'home','shiftleft'}:index=0
                else:index=len(visible)-1
                continue
            try:
                if key=='R':request('scan',node=owner);value=catalog();notice='Books folder scanned; shelf refreshed'
                elif key=='G':sort_reverse=not sort_reverse
                elif key=='I':show_preview=not show_preview;native.frame_cleared();last_frame=None
                elif key=='M':native_images=not native_images;native.frame_cleared();last_frame=None;notice='Auto image' if native_images and native.enabled else 'ASCII previews'
                elif key=='W':
                    notice=terminal_style.open_pane(Path.cwd());pane_help=notice.startswith('Shell opened beside LOOK');last_frame=None
                elif key=='P':
                    import clipboard_shelf
                    clipboard_shelf.show(fd=fd);last_frame=None
                elif key=='s':
                    shelves=['To explore','Favorites','All','Pending removals',*book_core.STATUSES]+sorted(set(value.get('collections',[]))|{name for r in value.get('entries',[]) for name in r.get('collections',[])}|{r.get('shelf') for r in value.get('entries',[]) if r.get('shelf')})
                    shelf=shelves[((shelves.index(shelf) if shelf in shelves else -1)+1)%len(shelves)];results=None;index=0
                elif key=='c':
                    name=ask('New collection name')
                    if name:request('collection',node=owner,name=name);value=catalog();notice='Created '+name
                elif key=='C' and chosen and results is None:
                    name=ask('Collection name · existing: '+', '.join(value.get('collections',[])))
                    if name:
                        selected=name not in chosen.get('collections',[])
                        request('collect',node=chosen.get('node',owner),id=chosen['id'],name=name,selected=selected)
                        value=catalog();notice=('Added to ' if selected else 'Removed from ')+name
                elif key=='f' and chosen and chosen.get('kind')!='subject':
                    if results is None:
                        request('favorite',node=chosen.get('node',owner),id=chosen['id'],selected=not chosen.get('favorite',False))
                        value=catalog();notice='Favorites updated'
                    elif owned_book(chosen,value) or (ask('Download “'+chosen['title']+'” to '+owner+' and add to Favorites? y/N') or '').casefold()=='y':
                        book=acquire_book(chosen,value,owner,favorite=True);select_library(book,favorite=True);notice='Saved to Favorites'
                elif key=='x' and chosen and results is None:
                    action='restore' if chosen.get('removal_due') else 'reject'
                    if action=='restore' or (ask('Hide and delete this starter download after 48 hours? Undo in Pending removals · y/N') or '').casefold()=='y':
                        request(action,node=chosen.get('node',owner),id=chosen['id']);value=catalog();notice='Restored' if action=='restore' else 'Pending removal · 48 hours to undo'
                elif key=='d':
                    mode=ask('Discover · p popular · n new arrivals · s subjects · r surprise me','p')
                    if mode:
                        selected={'p':'popular','n':'new','s':'subjects','r':'surprise'}.get(mode,mode)
                        query='';browse(selected)
                elif key=='g':
                    text=ask('Search Project Gutenberg',query)
                    if text:query=text;browse('search',text=text)
                elif key=='n' and results is not None and discovery and discovery.get('next_index'):
                    browse(discovery['mode'],discovery['subject'],discovery['text'],more=True)
                elif key=='i':
                    path=ask('Import EPUB or PDF · Tab completes · arrows open the path picker',path=True)
                    if path:import_files([path],owner);value=catalog();notice='Imported; source retained'
                elif key in {'enter','\r','\n'} and chosen:
                    if results is not None:
                        if chosen.get('kind')=='subject':browse('subject',chosen['subject']);continue
                        if owned_book(chosen,value):
                            select_library(owned_book(chosen,value));notice='Already on your Fabric shelf · selected existing copy; Enter reads';continue
                        answer=ask('Download “'+chosen['title']+'” to '+owner+'? y/N')
                        if answer and answer.casefold()=='y':
                            book=acquire_book(chosen,value,owner);select_library(book);notice='Book added to library on '+owner
                    else:
                        print('\nOpening reader; copying a remote book locally if needed…',flush=True)
                        path=local_copy(chosen)
                        if book_reader.preference()!='system' and not book_reader.binary('bookokrat'):
                            choice=ask('Terminal reader not installed · n installs Bookokrat with read-along · i standard Bookokrat · s system reader · Esc cancels')
                            if choice and choice.casefold()=='n':
                                import book_native
                                book_native.install(confirmed=True);notice='Native reader setup started; Enter retries when ready';continue
                            if choice and choice.casefold()=='i':
                                book_reader.install(confirmed=True);notice='Bookokrat setup started; Enter retries when ready · o opens system reader';continue
                            if not choice or choice.casefold()!='s':continue
                            mode='system'
                        else:mode=None
                        termios.tcsetattr(fd,termios.TCSADRAIN,old)
                        try:notice=book_reader.open_book(path,ui._desktop_launch,mode=mode)
                        finally:
                            tty.setcbreak(fd);last_frame=None
                            if os.environ.get('KITTY_WINDOW_ID') or os.environ.get('TERM')=='xterm-kitty':sys.stdout.write('\x1b_Ga=d,d=a,q=2\x1b\\')
                            sys.stdout.write('\x1b[0m\x1b[2J\x1b[H');sys.stdout.flush()
                elif chosen and results is None:
                    if key=='a':
                        import book_speech
                        native.frame_cleared()
                        if os.environ.get('KITTY_WINDOW_ID') or os.environ.get('TERM')=='xterm-kitty':sys.stdout.write('\x1b_Ga=d,d=a,q=2\x1b\\')
                        notice=book_speech.desk(ui,local_copy(chosen),chosen['title'],reading=chosen.get('reading'),save_reading=lambda fields:request('progress',node=chosen.get('node','local'),id=chosen['id'],fields=fields))
                        value=catalog();last_frame=None
                    elif key=='o':
                        notice=book_reader.open_book(local_copy(chosen),ui._desktop_launch,mode='system')
                    elif key=='y':
                        target='@'+chosen['node']+':'+chosen['path'] if chosen.get('node') else chosen['path']
                        look_renderer.copy_text(make_link(chosen['title'],target));notice='Copied a Notes-compatible file/Fabric link'
                    elif key=='k':book_core.Shelf().import_file(local_copy(chosen));value=catalog();notice='Saved in this computer’s books folder for offline reading'
                    elif key=='m':
                        state=chosen.get('status','To Read');request('update',node=chosen.get('node','local'),id=chosen['id'],fields={'status':book_core.STATUSES[(book_core.STATUSES.index(state)+1)%len(book_core.STATUSES)]});value=catalog()
                    elif key=='e':
                        fields={}
                        for field in ('title','author','shelf','position'):
                            answer=ask(field.title(),chosen.get(field,''))
                            if answer is None:fields={};break
                            fields[field]=answer
                        if fields:request('update',node=chosen.get('node','local'),id=chosen['id'],fields=fields);value=catalog();notice='Metadata saved; document bytes unchanged'
            except (OSError,ValueError,RuntimeError,KeyError,subprocess.SubprocessError) as exc:notice=str(exc)
    finally:
        previews.close();native.frame_cleared();native.close()
        termios.tcsetattr(fd,termios.TCSADRAIN,old);sys.stdout.write('\033[0m\n')


def main(args,ui):
    parser=argparse.ArgumentParser(prog='lk books',description='Fabric EPUB/PDF shelf and Gutenberg discovery; bk is an alias. In the terminal, / searches Library or Gutenberg (Tab switches source); g searches Gutenberg and d browses. Downloads stay on the configured owner; opening remote books makes a verified local cache copy.')
    parser.add_argument('action',nargs='?',default='shelf',choices=['shelf','list','scan','import','search','discover','fetch','reader','listen','voices','speech-setup','refill','collections','reject','restore','collect','favorite','unfavorite'])
    parser.add_argument('values',nargs='*',help='reader: status/install/native-install/auto/bookokrat/system; listen: FILE; other actions: query or path')
    parser.add_argument('--node',default=None,help='Library owner; defaults to configured media destination')
    parser.add_argument('--json',action='store_true')
    parser.add_argument('--start-index',type=int,default=1,help='Gutenberg catalogue cursor returned as next_index by search/discover --json')
    parser.add_argument('--chapter',type=int)
    parser.add_argument('--paragraph',type=int)
    selected=parser.parse_args(args);owner=selected.node or media_storage.settings()['node']
    try:
        if selected.action in {'listen','voices','speech-setup'}:
            import book_speech
            if selected.action=='voices':
                available=book_speech.voices();value={'voices':available,'standard':book_speech.standard_voices(available),'setup':book_speech.setup_status()}
            elif selected.action=='speech-setup':value=book_speech.setup(confirmed=True)
            else:
                if len(selected.values)!=1:raise ValueError('Use lk books listen FILE [--chapter N --paragraph N]')
                if not sys.stdin.isatty() or not sys.stdout.isatty():raise ValueError('Open read-aloud controls in a terminal')
                fd=sys.stdin.fileno();old=termios.tcgetattr(fd)
                try:
                    tty.setcbreak(fd)
                    book_speech.desk(ui,Path(selected.values[0]).expanduser(),chapter=selected.chapter,paragraph=selected.paragraph)
                finally:termios.tcsetattr(fd,termios.TCSADRAIN,old)
                return 0
            print(json.dumps(value,ensure_ascii=False,indent=2));return 0
        if selected.action=='refill':
            if selected.values:
                if selected.values[0] not in {'on','off'} or len(selected.values)>2:raise ValueError('Use lk books refill on [COUNT] or off --node OWNER')
                value=request('refill',node=owner,enabled=selected.values[0]=='on',target=int(selected.values[1]) if len(selected.values)>1 else 1000)
            else:value=request(node=owner).get('refill',{'enabled':False,'target':1000})
            print(json.dumps(value,indent=2));return 0
        if selected.action=='collections':
            value=request('collection',node=owner,name=' '.join(selected.values)) if selected.values else catalog()
            print(json.dumps({'collections':value.get('collections',[])},ensure_ascii=False,indent=2));return 0
        if selected.action in {'reject','restore','collect','favorite','unfavorite'}:
            if not selected.values:raise ValueError('Choose a book ID from lk books list --json')
            fields={'id':selected.values[0]}
            if selected.action=='collect':fields['name']=' '.join(selected.values[1:])
            if selected.action in {'favorite','unfavorite'}:fields['selected']=selected.action=='favorite'
            print(json.dumps(request('favorite' if selected.action=='unfavorite' else selected.action,node=owner,**fields),ensure_ascii=False,indent=2));return 0
        if selected.action=='reader':
            choice=selected.values[0] if selected.values else 'status'
            if len(selected.values)>1:raise ValueError('Choose reader status, install, native-install, auto, bookokrat or system')
            if choice=='native-install':
                import book_native
                value=book_native.install(confirmed=True)
            elif choice=='install':value=book_reader.install(confirmed=True)
            elif choice in book_reader.MODES:book_reader.preference(choice);value=book_reader.status()
            elif choice=='status':value=book_reader.status()
            else:raise ValueError('Choose reader status, install, native-install, auto, bookokrat or system')
            print(json.dumps(value,ensure_ascii=False) if selected.json else 'Reader: '+value['reader']+' · '+(value['version'] or 'Bookokrat not installed')+' · setup '+value['setup']['state']+' · native read-along: '+('installed' if value.get('native_narration',{}).get('installed') else 'lk books reader native-install'))
            return 0
        if selected.action=='shelf' and sys.stdin.isatty() and sys.stdout.isatty():return desk(ui,' '.join(selected.values),owner=owner)
        if selected.action in {'list','shelf'}:
            value=catalog();value=dict(value,entries=rows_for(value,' '.join(selected.values),shelf='All'))
        elif selected.action=='scan':value=request('scan',node=owner)
        elif selected.action=='import':
            if not selected.values:raise ValueError('Choose one or more EPUB/PDF files')
            value={'entries':import_files(selected.values,owner)}
        elif selected.action=='search':value=discover('search',query=' '.join(selected.values),start_index=selected.start_index)
        elif selected.action=='discover':value=discover(selected.values[0] if selected.values else 'popular',' '.join(selected.values[1:]),start_index=selected.start_index)
        else:
            if len(selected.values)!=1:raise ValueError('Choose one direct HTTPS EPUB/PDF URL')
            value=request('fetch',node=owner,url=selected.values[0])
        if value.get('book'):value=dict(value,entries=[value['book']])
        if selected.json:print(json.dumps(value,ensure_ascii=False))
        else:
            if value.get('warning'):print(value['warning'])
            for row in value.get('entries',[]):print(book_core.clean(row.get('title'))+' · '+book_core.clean(row.get('author'))+(' · '+row['url'] if row.get('url') else ''))
            if value.get('next_index'):print('More results: add --start-index '+str(value['next_index']))
            if not value.get('entries'):print('No books yet · lk books scan · lk books import FILE · lk books search QUERY')
            for warning in value.get('warnings',[]):print('Warning: '+book_core.clean(warning))
        return 0
    except (OSError,ValueError,RuntimeError,subprocess.SubprocessError) as exc:print('LOOK Books: '+book_core.clean(exc));return 1
