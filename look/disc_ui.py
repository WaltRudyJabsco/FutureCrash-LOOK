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
import unicodedata

PROGRESS_HINTS='Esc return · ↑↓ scroll · Shift-↑↓ page'


def interface_colors():
    try:from . import terminal_style
    except ImportError:import terminal_style
    return terminal_style.list_colors()


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
    def cell(value,size):
        text=''.join(c if c.isprintable() else ' ' for c in str(value))
        cells=lambda value:sum(0 if unicodedata.combining(c) else 2 if unicodedata.east_asian_width(c) in {'W','F'} else 1 for c in value)
        if cells(text)>size:
            clipped=''
            for char in text:
                if cells(clipped+char)>max(0,size-1):break
                clipped+=char
            text=clipped+'…'
        return text+' '*max(0,size-cells(text))
    columns=[('STATE',9),('%',7)]+([('TIME',8)] if width>=58 else [])
    title_width=max(1,width-3-sum(size+2 for _,size in columns))
    frame.append(ink('  '+cell('TITLE',title_width)+'  '+'  '.join(cell(label,size) for label,size in columns),'GRAY'))
    details=[]
    if jobs:
        chosen=jobs[index]
        details=wrapped_lines('SELECTED · '+chosen['title'],width)
        detail='PHASE · '+str(chosen.get('stage') or chosen['state'])
        if chosen.get('error'):detail+=' · '+str(chosen['error'])
        if chosen.get('estimated_remaining_seconds') is not None and active(chosen):detail+=' · ETA ~'+str(chosen['estimated_remaining_seconds']//60)+' min'
        details+=wrapped_lines(detail,width)
        details=details[:max(1,min(5,height//4))]
    usable=max(1,height-len(frame)-len(details)-5);top=max(0,index-usable+1)
    for n,job in enumerate(jobs[top:top+usable],top):
        status=job['state'];role='GREEN' if status=='complete' else 'RED' if status in {'failed','cancelled'} else 'YELLOW'
        selected=n==index
        elapsed=elapsed_seconds(job)
        progress=f"{job['percent']:.1f}%" if isinstance(job.get('percent'),(int,float)) else '—'
        parts=[(('› ' if selected else '  ')+cell(job['title'],title_width),'SELECT_FG' if selected else 'WHITE' if n%2==0 else 'CYAN'),
               ('  ','SELECT_GRAY' if selected else 'GRAY'),(cell(status,9),'SELECT_'+role if selected else role),
               ('  '+cell(progress,7),'SELECT_GRAY' if selected else 'GRAY')]
        if width>=58:parts.append(('  '+cell(f'{elapsed//60}:{elapsed%60:02d}',8),'SELECT_GRAY' if selected else 'GRAY'))
        line=colors['SELECT_BG'] if selected else ''
        for value,color in parts:line+=colors[color]+value
        frame.append(line+'\033[0m')
    if details:frame.extend(['']+[ink(line,'GRAY') for line in details])
    if not jobs:frame.append(ink('No jobs shown · n starts a new import','GRAY'))
    return frame


def elapsed_seconds(job):
    value=job.get('elapsed_seconds')
    if isinstance(value,(int,float)):return max(0,int(value))
    end=(job.get('finished') or job['created']) if job.get('state') in {'complete','failed','cancelled'} else time.time()
    return max(0,int(end-job['created']))


def summary(job):
    progress=f"{job['percent']:.1f}%" if isinstance(job.get('percent'),(int,float)) else 'working'
    elapsed=elapsed_seconds(job)
    eta=job.get('estimated_remaining_seconds');remaining=f' · ETA ~{eta//60}:{eta%60:02d}' if isinstance(eta,int) and active(job) else ''
    delivery=job.get('delivery') or {}
    library=' · library '+str(delivery.get('state'))+' / '+str(delivery.get('stage')) if delivery else (' · library failed: '+str(job['delivery_error']) if job.get('delivery_error') else '')
    owner=str(job.get('node') or '')
    return (owner+' · ' if owner else '')+f"{job['title']} · {job['state']} · {job['stage']} · {progress} · {elapsed//60}:{elapsed%60:02d}"+remaining+library


def active(job):
    return job.get('state') not in {'complete','failed','cancelled'} or (job.get('delivery') or {}).get('state') in {'queued','running'}


def wrapped_lines(value,width):
    """Wrap receipt text by terminal cells, including unbroken paths and titles."""
    limit=max(2,width-1);lines=[];line='';cells=0
    for char in str(value):
        if char=='\n':
            lines.append(line);line='';cells=0;continue
        if char=='\t':char=' '
        elif ord(char)<32 or 127<=ord(char)<160:char='?'
        size=0 if unicodedata.combining(char) else 2 if unicodedata.east_asian_width(char) in {'W','F'} else 1
        if cells+size>limit:
            # Prefer a word boundary; a long filename still makes forward progress.
            boundary=line.rfind(' ')
            if boundary>0:
                lines.append(line[:boundary]);line=line[boundary+1:]
                cells=sum(0 if unicodedata.combining(c) else 2 if unicodedata.east_asian_width(c) in {'W','F'} else 1 for c in line)
            else:lines.append(line);line='';cells=0
        line+=char;cells+=size
    lines.append(line)
    return lines


def progress_lines(jobs,width,colors):
    try:from . import terminal_style
    except ImportError:import terminal_style
    lines=[]
    for index,job in enumerate(jobs):
        # All continuations belong to the same logical row, never the next stripe.
        for line in wrapped_lines(summary(job),width):
            lines.append(terminal_style.list_row(colors['WHITE']+line,width,index=index,colors=colors))
    return lines


def progress_frame(lines,title,width,height,offset,hints,colors):
    try:from . import terminal_style
    except ImportError:import terminal_style
    footer=hints(PROGRESS_HINTS,width).splitlines()
    visible=max(1,height-1-len(footer));offset=max(0,min(offset,max(0,len(lines)-visible)))
    if len(lines)>visible:title+=f' · {offset+1}–{min(len(lines),offset+visible)}/{len(lines)}'
    header=terminal_style.list_row(colors['CYAN']+title,width,colors=colors)
    return [header,*lines[offset:offset+visible],*footer],offset


def progress_scroll(key,offset,page_size):
    if key=='up':return max(0,offset-1)
    if key=='down':return offset+1
    if key in {'pageup','shiftup'}:return max(0,offset-page_size)
    if key in {'pagedown','shiftdown'}:return offset+page_size
    return offset


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


def tv_details(request,prompt,metadata,titles,title_index):
    try:from . import disc_metadata
    except ImportError:import disc_metadata
    import re
    metadata=dict(metadata)
    title=prompt('Series / season / disc label',metadata.get('title') or '')
    metadata['title']=title
    candidates=[];release=None
    previous=metadata.get('discogs_release') or {}
    link=prompt('Discogs release/master link or r/m-number (0 skips; blank uses suggestion)',str(previous.get('id') or ''))
    if link and link!='0':
        try:
            found=request('discogs-release',{'id':link})
            if found.get('master'):
                editions=found.get('editions') or []
                print('BOX SET · '+found['master']['title'])
                for n,item in enumerate(editions,1):print(f"  {n}. {item['country']} · {item['year']} · {item['title']} · {item['format']} · r{item['id']}")
                if found.get('more_editions'):print('More editions exist; use a direct release link if yours is absent.')
                choice=prompt('Choose your edition number; 0 skips','1' if len(editions)==1 else '0')
                if choice=='0':found={}
                else:
                    if not choice.isdigit() or not 1<=int(choice)<=len(editions):raise ValueError('Edition choice out of range')
                    found=request('discogs-release',{'id':str(editions[int(choice)-1]['id'])})
            if not found.get('release'):raise ValueError('No edition selected')
            release=found['release']
            print('RELEASE · '+release['artist']+' - '+release['title']+' · '+release['year']+' · '+release['country']+' · '+release.get('formats',''))
            if prompt('Use this physical edition? y / n','y').casefold()=='y':
                candidates=[dict(item) for item in release['tracks']]
                discs=sorted({match[1] for item in candidates if (match:=re.match(r'^(?:DVD|CD)?(\d+)[.-]',item['position'],re.I))},key=int)
                if discs:
                    hint=re.search(r'\b(?:disc|disk)\s*(\d+)',title,re.I)
                    choice=prompt('Disc in this release: '+', '.join(discs)+' / all',hint[1] if hint and hint[1] in discs else 'all')
                    if choice!='all':
                        if choice not in discs:raise ValueError('Choose a listed disc or all')
                        candidates=[item for item in candidates if re.match(r'^(?:DVD|CD)?'+re.escape(choice)+r'[.-]',item['position'],re.I)]
                metadata['discogs_release']={key:release[key] for key in ('id','title','artist','source')}
                if not candidates:print('Edition has no usable contents list; trying series metadata.')
            else:release=None
        except (OSError,ValueError,RuntimeError) as exc:
            print('Discogs lookup · '+str(exc)+' · series lookup remains available.');release=None;candidates=[]
    series=metadata.get('series') or disc_metadata.series_query(title)
    source=release['source'] if release else metadata.get('source') or ''
    if prompt('Search TVmaze for series and episodes (sends series name)? y / n','y').casefold()=='y':
        query=prompt('Series name to search',series)
        try:
            matches=request('tv-lookup',{'query':query}).get('matches') or []
            for number,row in enumerate(matches,1):print(f"  {number}. {row['title']} · {row.get('year') or ''}")
            if matches:
                choice=prompt('Confirm series number; 0 keeps release labels','1' if len(matches)==1 else '0')
                if choice!='0':
                    if not choice.isdigit() or not 1<=int(choice)<=len(matches):raise ValueError('Series choice out of range')
                    show=matches[int(choice)-1];episodes=request('tv-episodes',{'id':show['id']}).get('episodes') or []
                    series=show['title'];source=show['source']
                    if candidates:
                        for item in candidates:
                            exact=[ep for ep in episodes if ep['title'].casefold()==item['title'].casefold()]
                            if len(exact)==1:item.update(exact[0])
                    else:candidates=episodes
            else:print('No series match; keeping available release labels.')
        except (OSError,ValueError,RuntimeError) as exc:print('TV lookup unavailable · '+str(exc)+' · keeping available labels.')
    if not candidates:return title,metadata
    for number,item in enumerate(candidates,1):
        print(f"  {number}. {item.get('position') or ''} {disc_metadata.episode_label(item)} · {item.get('duration') or str(item.get('runtime') or '?')+' min'} · {item.get('heading') or ''}")
    print('Match disc titles below. Numbers choose listed contents; x NAME labels an extra; 0 keeps unidentified. DVD title order is not episode order.')
    mapped={}
    for item in titles:
        index=str(item['index'])
        if title_index!='all' and index!=title_index:continue
        previous=(metadata.get('tv_titles') or {}).get(index,{})
        exact=[str(n) for n,ep in enumerate(candidates,1) if item.get('name','').casefold()==ep['title'].casefold()]
        suggestion=disc_metadata.duration_suggestion(item,candidates)
        default=exact[0] if len(exact)==1 else suggestion or '0'
        if not exact and suggestion:print('Duration suggests '+candidates[int(suggestion)-1]['title']+'; confirm against the disc contents.')
        if previous.get('content_kind')=='extra':default='x '+previous['title']
        else:
            for n,ep in enumerate(candidates,1):
                if previous.get('title')==ep.get('title') and previous.get('source')==ep.get('source'):default=str(n)
        answer=prompt(f"Disc title {index} · {item.get('name') or 'unnamed'} · {item.get('duration') or '?'}",default)
        if answer=='0':continue
        if answer.casefold().startswith('x '):selected={'title':answer[2:].strip(),'content_kind':'extra'}
        elif answer.isdigit() and 1<=int(answer)<=len(candidates):selected=dict(candidates[int(answer)-1])
        else:raise ValueError('Choose a listed content number, x NAME, or 0')
        selected.update(series=series,filename=item.get('filename') or '')
        mapped[index]=selected
    metadata.update(series=series,source=source,tv_titles=disc_metadata.validate_tv_titles(mapped))
    print('Content choices saved for review; unmatched titles remain unnamed.')
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
    fd=sys.stdin.fileno();old=termios.tcgetattr(fd);colors=interface_colors();offset=0
    try:
        tty.setcbreak(fd)
        while True:
            snapshot=request('jobs',{});jobs=snapshot['jobs'];current=[job for job in jobs if active(job)]
            shown=current or jobs[:1];width,height=shutil.get_terminal_size((100,30))
            lines=progress_lines(shown,width,colors)
            if not shown:lines.append('No imports yet')
            unavailable=snapshot.get('unavailable') or []
            if unavailable:lines.extend(colors['YELLOW']+line+'\033[0m' for line in wrapped_lines('Unavailable: '+', '.join(row['node'] for row in unavailable),width))
            if not current and shown:
                detail=shown[0].get('error') or (shown[0].get('delivery') or {}).get('error') or shown[0].get('output') or ''
                lines.extend(colors['GRAY']+line+'\033[0m' for line in wrapped_lines(detail,width))
            frame,offset=progress_frame(lines,'FABRIC IMPORT PROGRESS',width,height,offset,hints,colors)
            page_size=max(1,height-1-len(hints(PROGRESS_HINTS,width).splitlines()))
            sys.stdout.write('\033[2J\033[H'+'\n'.join(frame)+'\033[J');sys.stdout.flush()
            if not current and not snapshot.get('fabric') and len(lines)<=page_size:return 0 if not shown or (shown[0]['state']=='complete' and (shown[0].get('delivery') or {}).get('state') not in {'failed','cancelled'}) else 1
            key=read_key(fd,1)
            if key in {'esc','q','\x03'}:return 0
            offset=progress_scroll(key,offset,page_size)
    finally:termios.tcsetattr(fd,termios.TCSADRAIN,old);sys.stdout.write('\033[0m\n');sys.stdout.flush()


def capture(request,drive,kind,title='',destination='',title_index='',release=None,metadata=True,category=None):
    payload={'drive':drive,'kind':kind,'title':title,'destination':destination,'title_index':title_index}
    if category:payload['category']=category
    if kind=='cd' and metadata:
        scan=request('scan',{'drive':drive,'kind':kind});releases=scan.get('releases') or []
        if scan.get('metadata'):payload['metadata']=scan['metadata']
        if release is not None:
            if not 1<=release<=len(releases):raise ValueError('Release choice is out of range; scan first')
            payload['metadata']=releases[release-1]
        elif len(releases)==1:payload['metadata']=releases[0]
    return request('start',payload)


def watch(identifier,request,read_key,hints):
    fd=sys.stdin.fileno();old=termios.tcgetattr(fd);colors=interface_colors();offset=0
    try:
        tty.setcbreak(fd)
        while True:
            job=request('status',{'id':identifier})['job'];width,height=shutil.get_terminal_size((100,30))
            lines=progress_lines([job],width,colors)
            detail=job.get('error') or (job.get('delivery') or {}).get('error') or job.get('output') or job.get('partial_path') or ''
            lines.extend(colors['GRAY']+line+'\033[0m' for line in wrapped_lines(detail,width))
            frame,offset=progress_frame(lines,'FABRIC IMPORT',width,height,offset,hints,colors)
            page_size=max(1,height-1-len(hints(PROGRESS_HINTS,width).splitlines()))
            sys.stdout.write('\033[2J\033[H'+'\n'.join(frame)+'\033[J');sys.stdout.flush()
            if job['state'] in {'complete','failed','cancelled'} and (job.get('delivery') or {}).get('state') not in {'queued','running'} and len(lines)<=page_size:return 0 if job['state']=='complete' and (job.get('delivery') or {}).get('state') not in {'failed','cancelled'} and not job.get('delivery_error') else 1
            key=read_key(fd,1)
            if key in {'esc','q','\x03'}:return 0
            offset=progress_scroll(key,offset,page_size)
    finally:termios.tcsetattr(fd,termios.TCSADRAIN,old);sys.stdout.write('\033[0m\n');sys.stdout.flush()


class ImportBack(Exception):
    """Escape is navigation during setup, before any import is submitted."""


def import_options(request,inventory,drive,prompt,path_prompt):
    try:from . import disc_metadata,media_storage,fabric_files
    except ImportError:import disc_metadata,media_storage,fabric_files
    from pathlib import Path
    selected=next(row for row in inventory['drives'] if row['id']==drive)
    hint=disc_metadata.disc_hint(selected)
    kind=selected.get('kind') or hint['kind'] or 'cd'
    category='music' if kind=='cd' else 'movies'
    scan=None;scan_kind=None;metadata={};title='';title_index='';destination='';preferences=None
    step=0
    print('NEW IMPORT · Esc back; Esc at Disc kind cancels · nothing starts until review')
    while True:
        try:
            if step==0:
                value=prompt('Disc kind: cd / dvd / bluray',kind).casefold()
                if value not in {'cd','dvd','bluray'}:raise ValueError('Choose cd, dvd or bluray')
                if value!=kind:category='music' if value=='cd' else 'movies';destination='';scan=None
                kind=value
                if kind!='cd' and not inventory['tools'].get('makemkvcon'):
                    print('MakeMKV is needed for protected discs and lossless import. Official setup: https://www.makemkv.com/download/')
                    if prompt('Continue with HandBrake for an unprotected disc? y / n','n').casefold()!='y':return None
            elif step==1:
                value=prompt('Library category: music' if kind=='cd' else 'Library category: movie / tv',category).casefold()
                value={'movie':'movies','m':'movies','t':'tv'}.get(value,value)
                if value not in ({'music'} if kind=='cd' else {'movies','tv'}):raise ValueError('Choose music for CD, movie or tv for DVD/Blu-ray')
                if value!=category:destination='';title_index=''
                category=value
            elif step==2:
                if scan is None or scan_kind!=kind:
                    print('Scanning inserted disc…',flush=True)
                    try:scan=request('scan',{'drive':drive,'kind':kind})
                    except (OSError,ValueError,RuntimeError) as exc:
                        print('SCAN FAILED · '+str(exc)+' · no import started')
                        choice=prompt('r retry scan / b back / c cancel','c').casefold()
                        if choice=='r':continue
                        if choice=='b':step=1;continue
                        return None
                    scan_kind=kind
                    detected=scan.get('kind') or kind
                    if detected!=kind:
                        kind=detected;category='music' if kind=='cd' else 'movies';destination='';step=1;continue
                    metadata=dict(scan.get('metadata') or {});title='';title_index=''
                print('DISC · '+kind.upper()+' · '+str(scan.get('engine') or ''))
                if kind=='cd':
                    releases=scan.get('releases') or []
                    if not releases:
                        print('No automatic album match. Optional barcode lookup sends the digits to MusicBrainz.')
                        barcode=prompt('CD barcode digits (blank keeps disc labels)','')
                        if barcode:
                            found=request('cd-barcode',{'barcode':barcode}).get('releases') or []
                            for n,item in enumerate(found,1):print(f"  {n}. {item['title']} · {item.get('artist') or ''} · {item.get('date') or ''} · {item.get('country') or ''}")
                            if found:
                                choice=prompt('Confirm barcode release; 0 keeps disc labels','1' if len(found)==1 else '0')
                                if choice!='0':
                                    if not choice.isdigit() or not 1<=int(choice)<=len(found):raise ValueError('Release choice out of range')
                                    import time
                                    time.sleep(1)  # MusicBrainz asks for at most one request per second.
                                    releases=request('cd-release',{'id':found[int(choice)-1]['release_id']}).get('releases') or []
                                    releases=[item for item in releases if len(item.get('tracks') or [])==scan.get('tracks')]
                                    if not releases:print('Release track count does not match this disc; keeping disc labels.')
                            else:print('Barcode not found; keeping disc labels.')
                    for n,release in enumerate(releases,1):print(f"  {n}. {release['title']} · {release.get('artist') or ''}")
                    choice=prompt('Release number (blank keeps detected labels)','1' if len(releases)==1 else '') if releases else ''
                    if choice:
                        if not choice.isdigit() or not 1<=int(choice)<=len(releases):raise ValueError('Release choice out of range')
                        metadata=dict(releases[int(choice)-1])
                else:
                    for item in scan.get('titles') or []:print(f"  Title {item['index']} · {item.get('name') or 'Video title'} · {item.get('duration') or 'duration unavailable'}")
                    default='all' if category=='tv' and scan.get('engine')=='makemkv' else feature_index(scan.get('titles') or [])
                    title_index=prompt('Title index (all keeps every title with MakeMKV)',title_index or default)
                    if title_index!='all' and not title_index.isdigit():raise ValueError('Choose a title index or all')
            elif step==3:
                if kind=='cd':
                    title=prompt('Album title',title or metadata.get('title') or '')
                    metadata['artist']=prompt('Artist (optional)',metadata.get('artist') or '')
                elif category=='tv':
                    title,metadata=tv_details(request,prompt,dict(metadata,title=title or metadata.get('title') or hint.get('title') or ''),scan.get('titles') or [],title_index)
                else:title,metadata=movie_details(request,prompt,dict(metadata,title=title or metadata.get('title') or ''))
                if not title:raise ValueError('Give this import a name')
            elif step==4:
                default=media_storage.destination(kind,category)
                print('DESTINATION · Tab completes; →/↓ opens LOOK picker; Ctrl-U clears; Esc goes back')
                destination=path_prompt('Destination',destination or default)
                if not destination:raise ValueError('Choose a destination')
                target=fabric_files.parse(destination)
                preferences=None
                if destination.rstrip('/')!=default.rstrip('/'):
                    if target:values={'node':target.node,'root':target.path}
                    elif Path(destination.rstrip('/')).name==category:values={'node':inventory.get('node') or 'local','root':str(Path(destination).parent)}
                    else:values=None
                    if values and prompt('Remember this library for future imports? y / n','n').casefold()=='y':preferences=values
            else:
                target=fabric_files.parse(destination)
                actual=str(target)+('/'+category if target else '') if target else destination
                print(f"REVIEW · {title} · {kind.upper()} · {category} · title {title_index or 'audio tracks'}\nSave to {actual}")
                for index,item in (metadata.get('tv_titles') or {}).items():
                    print('  Title '+index+' → '+disc_metadata.episode_label(item))
                if category=='tv':print('Metadata · '+str(metadata.get('series') or 'series not identified')+' · '+str(len(metadata.get('tv_titles') or {}))+' matched titles · unmatched titles kept')
                print('y start · k kind · c category · i titles · m name/metadata · d destination · Esc back')
                choice=prompt('Start or edit','y').casefold()
                if choice=='y':return {'drive':drive,'kind':kind,'category':category,'title':title,'destination':destination,'title_index':title_index,'metadata':metadata,'preferences':preferences}
                edits={'k':0,'c':1,'i':2,'m':3,'d':4}
                if choice in edits:step=edits[choice];continue
                if choice in {'n','cancel'}:return None
                raise ValueError('Choose y to start, an edit letter, or Escape to go back')
            step+=1
        except ImportBack:
            if step==0:return None
            step-=1
        except (OSError,ValueError,RuntimeError) as exc:
            print('IMPORT SETUP · '+str(exc))


def workspace(request,read_key,hints):
    fd=sys.stdin.fileno();old=termios.tcgetattr(fd);index=0;notice='';inventory=request('drives',{});show_history=True;colors=interface_colors()
    def prompt(label,default='',path=False):
        termios.tcsetattr(fd,termios.TCSADRAIN,old);sys.stdout.write('\033[?25h');sys.stdout.flush()
        try:
            try:from . import look_renderer
            except ImportError:import look_renderer
            from pathlib import Path
            caption=label+' › '
            value,cancelled=look_renderer.prompt_line(caption,initial=default,picker_root=Path.cwd() if path else None)
            if cancelled:raise ImportBack()
            return value.strip() or default
        finally:tty.setcbreak(fd);sys.stdout.write('\033[?25l')
    try:
        tty.setcbreak(fd);sys.stdout.write('\033[?25l')
        while True:
            jobs=request('jobs',{})['jobs']
            if not show_history:jobs=[job for job in jobs if active(job)]
            index=max(0,min(index,max(0,len(jobs)-1)))
            width,height=shutil.get_terminal_size((100,30))
            controls=hints('n new import · d discover · h history · ↑↓ jobs · Enter progress · l send to library · c cancel · x dismiss finished · Esc exit',width)
            frame=workbench_lines(inventory,jobs,index,width,height-max(0,len(controls.splitlines())-2),show_history,colors)
            frame.extend(['',controls,notice])
            sys.stdout.write('\033[2J\033[H'+'\n'.join(line[:width-1] if '\033' not in line else line for line in frame)+'\033[J');sys.stdout.flush()
            key=read_key(fd,1)
            if key in {'n','d','h','l','c','x'}:key=key.upper()
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
                    destination=media_storage.destination(jobs[index]['kind'],jobs[index].get('category'))
                    if not destination.startswith('@'):raise ValueError('Choose a library node first with lk media storage --node NODE --root PATH')
                    request('deliver',{'id':jobs[index]['id'],'destination':destination})
                    notice='Delivery started; originals kept. Enter shows progress.'
                elif key=='X' and jobs:
                    if active(jobs[index]):raise ValueError('Finish or cancel the job before dismissing it')
                    if prompt('Dismiss '+jobs[index]['title']+' from the list? Type yes; media and receipts stay')=='yes':
                        request('dismiss',{'id':jobs[index]['id']});notice='Dismissed from list; media and receipts retained'
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
                    payload=import_options(request,inventory,drive,prompt,lambda label,default:prompt(label,default,path=True))
                    if payload is None:notice='New import cancelled; existing jobs unchanged';continue
                    preferences=payload.pop('preferences')
                    request('start',payload)
                    if preferences:
                        try:from . import media_storage
                        except ImportError:import media_storage
                        media_storage.settings(preferences)
                    index=0;notice='Import started on the drive owner'
            except ImportBack:notice='Cancelled; existing jobs unchanged'
            except (OSError,ValueError,RuntimeError) as exc:notice=str(exc)
    finally:termios.tcsetattr(fd,termios.TCSADRAIN,old);sys.stdout.write('\033[?25h\033[0m\n');sys.stdout.flush()


def main(argv,request_factory,read_key,hints):
    parser=argparse.ArgumentParser(prog='lk media import',description='CD/DVD/Blu-ray import on the node owning the drive. No arguments opens the workbench.')
    parser.add_argument('action',nargs='?',choices=['drives','scan','start','jobs','status','watch','cancel','deliver','dismiss'])
    parser.add_argument('id',nargs='*',help='Album name, latest, short ID, or full ID; watch defaults to all active work, deliver offers completed imports')
    parser.add_argument('--node',help='Drive-owner node; watch/jobs default to Fabric, other actions to local')
    parser.add_argument('--drive',help='Drive ID shown by drives')
    parser.add_argument('--kind',choices=['cd','dvd','bluray'],default='cd')
    parser.add_argument('--category',choices=['music','movies','tv'],help='Library category; CD defaults to music, video to movies')
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
            result=capture(request,args.drive,args.kind,args.title,args.destination or media_storage.destination(args.kind,args.category),args.title_index,args.release,not args.no_metadata,args.category)
        else:
            if action in {'status','cancel','deliver','dismiss'}:
                if action in {'cancel','dismiss'} and not selector:raise ValueError(action+' requires an album name or job ID')
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
