"""Optical workbench: local or paired-node jobs through one request adapter."""
from __future__ import annotations
import argparse
import json
import shutil
import sys
import termios
import time
import tty
import os


def interface_colors():
    try:from . import terminal_style
    except ImportError:import terminal_style
    palette=terminal_style.application_colors()
    defaults={'CYAN':'36','GREEN':'32','RED':'31','YELLOW':'33','WHITE':'97','GRAY':'90'}
    colors={role:'\033['+('38;2;'+';'.join(map(str,palette[role])) if role in palette else code)+'m'
            for role,code in defaults.items()}
    name=os.environ.get('LOOK_TERMINAL_THEME','')
    if not name:
        try:name=(terminal_style.directory()/'look-theme.conf').read_text().splitlines()[0].removeprefix('# LOOK palette: ')
        except (OSError,IndexError):name='neon'
    try:selected=terminal_style.settings(name)
    except (OSError,ValueError):selected=terminal_style.settings('neon')
    background=selected['selection_background'];foreground=selected['selection_foreground']
    if terminal_style.contrast(background,foreground)<4.5:foreground=terminal_style.readable_text(background)
    def rgb(value):return tuple(int(value[i:i+2],16) for i in (1,3,5))
    def escape(value,channel='38'):return '\033['+channel+';2;'+';'.join(map(str,rgb(value)))+'m'
    colors['SELECT_BG']=escape(background,'48');colors['SELECT_FG']=escape(foreground)
    for role,key in {'GREEN':'color114','RED':'color203','YELLOW':'color221','GRAY':'color8'}.items():
        original=selected.get(key) or foreground
        # Preserve the ink hue where possible, moving toward selection text for contrast.
        for step in range(11):
            amount=step/10
            candidate='#'+''.join(f'{round(a*(1-amount)+b*amount):02x}' for a,b in zip(rgb(original),rgb(foreground)))
            if terminal_style.contrast(background,candidate)>=4.5:break
        colors['SELECT_'+role]=escape(candidate)
    return colors


def workbench_lines(inventory,jobs,index,width,height,show_history,colors):
    def ink(value,role):return colors[role]+str(value)+'\033[0m'
    frame=[ink('FABRIC DISC WORKBENCH','CYAN')+' · '+ink(inventory.get('node') or 'local','WHITE'),'']
    for row in inventory['drives']:
        disc=(row.get('disc') or '').replace('_',' ') or 'No named disc detected'
        frame.append(ink('INSERTED DISC  ','GRAY')+'\033[1m'+ink(disc,'GREEN'))
        frame.append(ink('DRIVE          ','GRAY')+ink(row['label'],'WHITE')+' · '+ink(row['id'],'GRAY'))
    if not inventory['drives']:frame.append(ink('No optical drive detected · connect one and press d','YELLOW'))
    else:frame.append(ink('n imports the inserted disc · d refreshes discovery','YELLOW'))
    frame.append(ink('TOOLS  ','CYAN')+ink(', '.join(name for name,path in inventory['tools'].items() if path),'GRAY'))
    frame.extend(['',ink('IMPORT JOBS','CYAN')+' · '+ink('active + saved history' if show_history else 'active only','GRAY')])
    usable=max(1,height-len(frame)-4);top=max(0,index-usable+1)
    for n,job in enumerate(jobs[top:top+usable],top):
        prefix=('› ' if n==index else '  ')
        body=summary(job)
        title=job['title'];owner=str(job.get('node') or '')
        subject=(owner+' · ' if owner else '')+title
        status=job['state'];tail=body[len(subject)+3+len(status):]
        # Remove the repeated phase in terminal receipts: "complete · complete".
        if job.get('stage')==status:tail=tail.removeprefix(' · '+status)
        role='GREEN' if status=='complete' else 'RED' if status in {'failed','cancelled'} else 'YELLOW'
        selected=n==index
        parts=[(prefix,'SELECT_FG' if selected else 'GRAY'),
               (subject,'SELECT_FG' if selected else 'WHITE' if n%2==0 else 'CYAN'),
               (' · ','SELECT_GRAY' if selected else 'GRAY'),
               (status,'SELECT_'+role if selected else role),(tail,'SELECT_GRAY' if selected else 'GRAY')]
        remaining=max(0,width-1);line=colors['SELECT_BG'] if selected else ''
        for value,color in parts:
            value=value[:remaining];remaining-=len(value);line+=colors[color]+value
        if selected:line+=' '*remaining
        frame.append(line+'\033[0m')
    if not jobs:frame.append(ink('No jobs shown · n starts a new import','GRAY'))
    return frame


def summary(job):
    progress=f"{job['percent']:.1f}%" if isinstance(job.get('percent'),(int,float)) else 'working'
    elapsed=int(job.get('elapsed_seconds') or max(0,time.time()-job['created']))
    eta=job.get('estimated_remaining_seconds');remaining=f' · ETA ~{eta//60}:{eta%60:02d}' if isinstance(eta,int) else ''
    delivery=job.get('delivery') or {}
    library=' · library '+str(delivery.get('state'))+' / '+str(delivery.get('stage')) if delivery else (' · library failed: '+str(job['delivery_error']) if job.get('delivery_error') else '')
    owner=str(job.get('node') or '')
    return (owner+' · ' if owner else '')+f"{job['title']} · {job['state']} · {job['stage']} · {progress} · {elapsed//60}:{elapsed%60:02d}"+remaining+library


def active(job):
    return job.get('state') not in {'complete','failed','cancelled'} or (job.get('delivery') or {}).get('state') in {'queued','running'}


def movie_details(request,prompt,metadata):
    metadata=dict(metadata)
    title=prompt('Movie name (disc label is a suggestion)',metadata.get('title') or '')
    metadata['title']=title
    if prompt('Search Wikidata for title/year (sends movie name)? y / n','y').casefold()=='y':
        try:
            result=request('movie-lookup',{'query':title})
            matches=result.get('matches') or []
            for number,row in enumerate(matches,1):
                print(f"  {number}. {row['title']} · {row.get('year') or 'year unknown'} · {row.get('description') or ''}")
            if matches:
                choice=prompt('Confirm match number; 0 keeps your entered name','1' if len(matches)==1 else '0')
                if choice!='0':
                    if not choice.isdigit() or not 1<=int(choice)<=len(matches):raise ValueError('Movie match out of range')
                    selected=matches[int(choice)-1];metadata.update(selected)
                    title=selected['title']+(f" ({selected['year']})" if selected.get('year') else '')
            else:print('No matching movie found; keeping your name.')
        except (OSError,ValueError,RuntimeError) as exc:print('Movie lookup unavailable · '+str(exc)+' · keeping your name.')
    return title,metadata


def feature_index(titles):
    def duration(row):
        try:
            seconds=0
            for part in row.get('duration','').split(':'):seconds=seconds*60+int(part)
            return seconds
        except ValueError:return 0
    longest=max(titles,key=duration,default={})
    return str(longest.get('index','')) if duration(longest)>=600 else ''


def resolve_job(request,selector,action):
    """Resolve human names without guessing which album a mutation should affect."""
    import re
    if re.fullmatch('[0-9a-f]{32}',selector):return selector
    jobs=request('jobs',{})['jobs']
    eligible=[job for job in jobs if action!='deliver' or job.get('state')=='complete']
    if selector.casefold()=='latest':eligible=eligible[:1]
    elif selector:
        exact=[job for job in eligible if str(job.get('title','')).casefold()==selector.casefold()]
        eligible=exact or [job for job in eligible if selector.casefold() in
                          (str(job.get('title',''))+' '+str((job.get('metadata') or {}).get('artist',''))).casefold()
                          or job['id'].startswith(selector)]
    elif action=='deliver':
        eligible=[job for job in eligible if (job.get('delivery') or {}).get('state')!='complete']
    if not eligible:raise ValueError('No matching '+('undelivered completed imports' if action=='deliver' and not selector else 'imports'))
    if len(eligible)==1:return eligible[0]['id']
    labels=[str(job['title'])+' · '+str((job.get('metadata') or {}).get('artist') or 'artist unknown') for job in eligible]
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        raise ValueError('More than one import matches; choose an album name: '+', '.join(labels))
    for number,label in enumerate(labels,1):print(f'  {number}. {label}')
    choice=input('Choose album number (blank cancels) › ').strip()
    if not choice:raise ValueError('Delivery cancelled' if action=='deliver' else 'Selection cancelled')
    if not choice.isdigit() or not 1<=int(choice)<=len(eligible):raise ValueError('Album choice out of range')
    return eligible[int(choice)-1]['id']


def watch_all(request,read_key,hints):
    """Follow active imports and deliveries, or show the most recent result."""
    fd=sys.stdin.fileno();old=termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)
        while True:
            snapshot=request('jobs',{});jobs=snapshot['jobs'];current=[job for job in jobs if active(job)]
            shown=current or jobs[:1];width,height=shutil.get_terminal_size((100,30))
            frame=['\033[1;38;5;117mFABRIC IMPORT PROGRESS\033[0m']
            frame.extend(summary(job) for job in shown[:max(1,height-4)])
            if not shown:frame.append('No imports yet')
            unavailable=snapshot.get('unavailable') or []
            if unavailable:frame.append('Unavailable: '+', '.join(row['node'] for row in unavailable))
            if not current and shown:
                frame.append(shown[0].get('error') or (shown[0].get('delivery') or {}).get('error') or shown[0].get('output') or '')
            frame.append(hints('Esc return · Jobs continue in background',width))
            sys.stdout.write('\033[2J\033[H'+'\n'.join(line[:width-1] if '\033' not in line else line for line in frame)+'\033[J');sys.stdout.flush()
            if not current and not snapshot.get('fabric'):return 0 if not shown or (shown[0]['state']=='complete' and (shown[0].get('delivery') or {}).get('state') not in {'failed','cancelled'}) else 1
            if read_key(fd,1) in {'esc','q','\x03'}:return 0
    finally:termios.tcsetattr(fd,termios.TCSADRAIN,old);sys.stdout.write('\033[0m\n');sys.stdout.flush()


def capture(request,drive,kind,title='',destination='',title_index='',release=None,metadata=True):
    payload={'drive':drive,'kind':kind,'title':title,'destination':destination,'title_index':title_index}
    if kind=='cd' and metadata:
        scan=request('scan',{'drive':drive,'kind':kind});releases=scan.get('releases') or []
        if scan.get('metadata'):payload['metadata']=scan['metadata']
        if release is not None:
            if not 1<=release<=len(releases):raise ValueError('Release choice is out of range; scan first')
            payload['metadata']=releases[release-1]
        elif len(releases)==1:payload['metadata']=releases[0]
    return request('start',payload)


def watch(identifier,request,read_key,hints):
    fd=sys.stdin.fileno();old=termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)
        while True:
            job=request('status',{'id':identifier})['job'];width,height=shutil.get_terminal_size((100,30))
            frame=['\033[1;38;5;117mFABRIC IMPORT\033[0m',summary(job),job.get('error') or (job.get('delivery') or {}).get('error') or job.get('output') or job.get('partial_path') or '',hints('Esc return · Job continues in background',width)]
            sys.stdout.write('\033[2J\033[H'+'\n'.join(line[:width-1] if '\033' not in line else line for line in frame)+'\033[J');sys.stdout.flush()
            if job['state'] in {'complete','failed','cancelled'} and (job.get('delivery') or {}).get('state') not in {'queued','running'}:return 0 if job['state']=='complete' and (job.get('delivery') or {}).get('state') not in {'failed','cancelled'} and not job.get('delivery_error') else 1
            if read_key(fd,1) in {'esc','q','\x03'}:return 0
    finally:termios.tcsetattr(fd,termios.TCSADRAIN,old);sys.stdout.write('\033[0m\n');sys.stdout.flush()


def workspace(request,read_key,hints):
    fd=sys.stdin.fileno();old=termios.tcgetattr(fd);index=0;notice='';inventory=request('drives',{});show_history=True;colors=interface_colors()
    def prompt(label,default=''):
        termios.tcsetattr(fd,termios.TCSADRAIN,old);sys.stdout.write('\033[?25h');sys.stdout.flush()
        try:return input(label+(f' [{default}]' if default else '')+' › ').strip() or default
        finally:tty.setcbreak(fd);sys.stdout.write('\033[?25l')
    try:
        tty.setcbreak(fd);sys.stdout.write('\033[?25l')
        while True:
            jobs=request('jobs',{})['jobs']
            if not show_history:jobs=[job for job in jobs if active(job)]
            index=max(0,min(index,max(0,len(jobs)-1)))
            width,height=shutil.get_terminal_size((100,30))
            frame=workbench_lines(inventory,jobs,index,width,height,show_history,colors)
            frame.extend(['',hints('n import · d discover · h history · ↑↓ jobs · Enter progress · l send to library · c cancel · Esc exit',width),notice])
            sys.stdout.write('\033[2J\033[H'+'\n'.join(line[:width-1] if '\033' not in line else line for line in frame)+'\033[J');sys.stdout.flush()
            key=read_key(fd,1)
            if key in {'n','d','h','l','c'}:key=key.upper()
            if key in {'esc','q','\x03'}:return 0
            try:
                if key=='D':inventory=request('drives',{});notice='Discovery refreshed'
                elif key=='H':show_history=not show_history;notice='History '+('shown' if show_history else 'hidden; receipts and files kept')
                elif key=='up':index-=1
                elif key=='down':index+=1
                elif key in {'\r','\n'} and jobs:
                    watch(jobs[index]['id'],request,read_key,hints)
                elif key=='L' and jobs:
                    try:from . import media_storage
                    except ImportError:import media_storage
                    destination=media_storage.destination(jobs[index]['kind'])
                    if not destination.startswith('@'):raise ValueError('Choose a library node first with lk media storage --node NODE --root PATH')
                    request('deliver',{'id':jobs[index]['id'],'destination':destination})
                    notice='Delivery started; originals kept. Enter shows progress.'
                elif key=='C' and jobs:
                    if prompt('Cancel selected import? Type yes')=='yes':request('cancel',{'id':jobs[index]['id']});notice='Cancellation requested; partial files retained'
                elif key=='N':
                    available=inventory['drives']
                    if len(available)==1:drive=available[0]['id']
                    else:
                        for number,row in enumerate(available,1):print(f"  {number}. {row['label']} · {row.get('disc') or 'disc name unavailable'}")
                        choice=prompt('Drive number')
                        if not choice.isdigit() or not 1<=int(choice)<=len(available):raise ValueError('Connect a drive and choose its number')
                        drive=available[int(choice)-1]['id']
                    try:from . import disc_metadata
                    except ImportError:import disc_metadata
                    selected=next(row for row in available if row['id']==drive)
                    hint=disc_metadata.disc_hint(selected)
                    kind=selected.get('kind') or hint['kind'] or prompt('Disc kind: cd / dvd / bluray','cd')
                    if kind!='cd' and not inventory['tools'].get('makemkvcon'):
                        print('MakeMKV is needed for protected discs and lossless video import.\nOfficial setup: https://www.makemkv.com/download/\nInstall it on the drive owner, then press D to rediscover.')
                        if prompt('Continue with HandBrake for an unprotected disc? y / n','n').casefold()!='y':continue
                    scan=request('scan',{'drive':drive,'kind':kind})
                    kind=scan.get('kind') or kind
                    termios.tcsetattr(fd,termios.TCSADRAIN,old)
                    print('\nDISC · '+kind.upper()+' · '+str(scan.get('engine') or ''))
                    for number,release in enumerate(scan.get('releases') or [],1):
                        print(f"  {number}. {release['title']} · {release['artist']} · {len(release.get('tracks') or [])} tracks")
                    for title in scan.get('titles') or []:
                        print('  Title '+str(title['index'])+' · '+str(title.get('name') or 'Movie title')+' · '+str(title.get('duration') or 'duration unavailable'))
                    if kind=='cd' and not scan.get('releases'):print('  No matching release · keeping detected album and track names')
                    tty.setcbreak(fd)
                    metadata=dict(scan.get('metadata') or {});title_index=''
                    if kind=='cd':
                        releases=scan.get('releases') or []
                        choice='1' if len(releases)==1 else prompt('Release number (blank keeps detected labels)') if releases else ''
                        if choice:
                            number=int(choice)
                            if not 1<=number<=len(releases):raise ValueError('Release choice out of range')
                            metadata=releases[number-1]
                        if not metadata.get('artist'):
                            artist=prompt('Artist (optional; Return keeps Unknown artist)')
                            if artist:metadata['artist']=artist
                    else:title_index=prompt('Title index (suggested longest feature; type all for every title)',feature_index(scan.get('titles') or []))
                    if kind=='cd':title=prompt('Album title',metadata.get('title') or '')
                    else:title,metadata=movie_details(request,prompt,metadata)
                    import media_storage
                    destination=prompt('Destination (local folder or @node:library-root)',media_storage.destination(kind))
                    if destination!=media_storage.destination(kind):
                        from pathlib import Path
                        try:from . import fabric_files
                        except ImportError:import fabric_files
                        remote=fabric_files.parse(destination)
                        category='music' if kind=='cd' else 'movies'
                        if remote:values={'node':remote.node,'root':remote.path}
                        elif Path(destination).name==category:values={'node':inventory.get('node') or 'local','root':str(Path(destination).parent)}
                        else:values=None
                        if values and prompt('Remember this library for future imports? y / n','y').casefold()=='y':media_storage.settings(values)
                    print(f'Import {title} · {kind.upper()} · title {title_index or "audio tracks"}\nSave to {destination}')
                    if prompt('Start this import? y / n','y').casefold()!='y':continue
                    request('start',{'drive':drive,'kind':kind,'title':title,'destination':destination,'title_index':title_index,'metadata':metadata})
                    index=0;notice='Import started on the drive owner'
            except (OSError,ValueError,RuntimeError) as exc:notice=str(exc)
    finally:termios.tcsetattr(fd,termios.TCSADRAIN,old);sys.stdout.write('\033[?25h\033[0m\n');sys.stdout.flush()


def main(argv,request_factory,read_key,hints):
    parser=argparse.ArgumentParser(prog='lk media import',description='CD/DVD/Blu-ray import on the node owning the drive. No arguments opens the workbench.')
    parser.add_argument('action',nargs='?',choices=['drives','scan','start','jobs','status','watch','cancel','deliver'])
    parser.add_argument('id',nargs='*',help='Album name, latest, short ID, or full ID; watch defaults to all active work, deliver offers completed imports')
    parser.add_argument('--node',help='Drive-owner node; watch/jobs default to Fabric, other actions to local')
    parser.add_argument('--drive',help='Drive ID shown by drives')
    parser.add_argument('--kind',choices=['cd','dvd','bluray'],default='cd')
    parser.add_argument('--title',default='',help='Album/movie label')
    parser.add_argument('--title-index',default='',help='Video title index from scan, or all for MakeMKV')
    parser.add_argument('--destination',default='',help='Local import folder or @node:library-root; otherwise remembered storage default')
    parser.add_argument('--release',type=int,help='MusicBrainz release number from scan (starting at 1)')
    parser.add_argument('--no-metadata',action='store_true',help='Skip the MusicBrainz lookup for CD capture')
    parser.add_argument('--json',action='store_true')
    args=parser.parse_args(argv);selector=' '.join(args.id)
    fabric=args.node is None and (args.action=='jobs' or (args.action=='watch' and not selector))
    request=request_factory('fabric' if fabric else args.node)
    try:
        if not args.action and sys.stdin.isatty() and sys.stdout.isatty():return workspace(request,read_key,hints)
        action=args.action or 'drives'
        if action=='watch':
            if not selector:
                if sys.stdin.isatty() and sys.stdout.isatty():return watch_all(request,read_key,hints)
                snapshot=request('jobs',{});jobs=snapshot['jobs'];shown=[job for job in jobs if active(job)] or jobs[:1]
                if args.json:print(json.dumps(dict(snapshot,jobs=shown),ensure_ascii=False,indent=2))
                else:
                    print('\n'.join(summary(job) for job in shown) or 'No imports yet')
                    if snapshot.get('unavailable'):print('Unavailable: '+', '.join(row['node'] for row in snapshot['unavailable']))
                return 0
            selector=resolve_job(request,selector,action)
            if sys.stdin.isatty() and sys.stdout.isatty():return watch(selector,request,read_key,hints)
            action='status'
        if action=='start':
            import media_storage
            result=capture(request,args.drive,args.kind,args.title,args.destination or media_storage.destination(args.kind),args.title_index,args.release,not args.no_metadata)
        else:
            if action in {'status','cancel','deliver'}:
                if action=='cancel' and not selector:raise ValueError('cancel requires an album name or job ID')
                if not selector and action!='deliver':selector='latest'
                selector=resolve_job(request,selector,action)
            destination=args.destination
            if action=='deliver' and not destination:
                try:from . import media_storage
                except ImportError:import media_storage
                destination=media_storage.destination(args.kind)
                if not destination.startswith('@'):raise ValueError('Choose a library node first with lk media storage --node NODE --root PATH')
            result=request(action,{'drive':args.drive,'kind':args.kind,'id':selector,'destination':destination})
            if action=='deliver' and not args.json:
                print('Delivery started to '+destination.split(':',1)[0].lstrip('@')+'. Originals kept.\nRun lk media import watch for progress.')
                return 0
        print(json.dumps(result,ensure_ascii=False,indent=2));return 0
    except (OSError,ValueError,RuntimeError) as exc:print('LOOK IMPORT · '+str(exc),file=sys.stderr);return 1
