"""Optical workbench: local or paired-node jobs through one request adapter."""
from __future__ import annotations
import argparse
import json
import shutil
import sys
import termios
import time
import tty


def summary(job):
    progress=f"{job['percent']:.1f}%" if isinstance(job.get('percent'),(int,float)) else 'working'
    elapsed=int(job.get('elapsed_seconds') or max(0,time.time()-job['created']))
    eta=job.get('estimated_remaining_seconds');remaining=f' · ETA ~{eta//60}:{eta%60:02d}' if isinstance(eta,int) else ''
    delivery=job.get('delivery') or {}
    library=' · library '+str(delivery.get('state'))+' / '+str(delivery.get('stage')) if delivery else (' · library failed: '+str(job['delivery_error']) if job.get('delivery_error') else '')
    return f"{job['id'][:8]} · {job['title']} · {job['state']} · {job['stage']} · {progress} · {elapsed//60}:{elapsed%60:02d}"+remaining+library


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
    fd=sys.stdin.fileno();old=termios.tcgetattr(fd);index=0;notice='';inventory=request('drives',{})
    def prompt(label,default=''):
        termios.tcsetattr(fd,termios.TCSADRAIN,old);sys.stdout.write('\033[?25h');sys.stdout.flush()
        try:return input(label+(f' [{default}]' if default else '')+' › ').strip() or default
        finally:tty.setcbreak(fd);sys.stdout.write('\033[?25l')
    try:
        tty.setcbreak(fd);sys.stdout.write('\033[?25l')
        while True:
            jobs=request('jobs',{})['jobs'];index=max(0,min(index,max(0,len(jobs)-1)))
            width,height=shutil.get_terminal_size((100,30))
            frame=['\033[1;38;5;117mFABRIC DISC WORKBENCH\033[0m · '+str(inventory.get('node') or 'local')]
            frame.extend('DRIVE '+row['id']+' · '+row['label']+' · '+row.get('disc','') for row in inventory['drives'])
            if not inventory['drives']:frame.append('No optical drive detected · connect one and press D')
            frame.append('TOOLS '+', '.join(name for name,path in inventory['tools'].items() if path))
            usable=max(1,height-len(frame)-4);top=max(0,index-usable+1)
            for n,job in enumerate(jobs[top:top+usable],top):frame.append(('› ' if n==index else '  ')+summary(job))
            frame.extend(['',hints('N import · D discover · ↑↓ jobs · Enter progress · C cancel · Esc exit',width),notice])
            sys.stdout.write('\033[2J\033[H'+'\n'.join(line[:width-1] if '\033' not in line else line for line in frame)+'\033[J');sys.stdout.flush()
            key=read_key(fd,1)
            if key in {'esc','q','\x03'}:return 0
            try:
                if key=='D':inventory=request('drives',{});notice='Discovery refreshed'
                elif key=='up':index-=1
                elif key=='down':index+=1
                elif key in {'\r','\n'} and jobs:
                    watch(jobs[index]['id'],request,read_key,hints)
                elif key=='C' and jobs:
                    if prompt('Cancel selected import? Type yes')=='yes':request('cancel',{'id':jobs[index]['id']});notice='Cancellation requested; partial files retained'
                elif key=='N':
                    available=inventory['drives'];drive=prompt('Drive ID',available[0]['id'] if len(available)==1 else '')
                    kind=prompt('Disc kind: cd / dvd / bluray','cd')
                    scan=request('scan',{'drive':drive,'kind':kind})
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
                    else:title_index=prompt('Title index from scan (or all with MakeMKV)')
                    title=prompt('Album / movie title',metadata.get('title') or '')
                    import media_storage
                    destination=prompt('Destination (local folder or @node:library-root)',media_storage.destination(kind))
                    request('start',{'drive':drive,'kind':kind,'title':title,'destination':destination,'title_index':title_index,'metadata':metadata})
                    index=0;notice='Import started on the drive owner'
            except (OSError,ValueError,RuntimeError) as exc:notice=str(exc)
    finally:termios.tcsetattr(fd,termios.TCSADRAIN,old);sys.stdout.write('\033[?25h\033[0m\n');sys.stdout.flush()


def main(argv,request_factory,read_key,hints):
    parser=argparse.ArgumentParser(prog='lk media import',description='CD/DVD/Blu-ray import on the node owning the drive. No arguments opens the workbench.')
    parser.add_argument('action',nargs='?',choices=['drives','scan','start','jobs','status','watch','cancel','deliver'])
    parser.add_argument('id',nargs='?',help='Full job ID for status/watch/cancel')
    parser.add_argument('--node',help='Paired drive-owner node; defaults to local')
    parser.add_argument('--drive',help='Drive ID shown by drives')
    parser.add_argument('--kind',choices=['cd','dvd','bluray'],default='cd')
    parser.add_argument('--title',default='',help='Album/movie label')
    parser.add_argument('--title-index',default='',help='Video title index from scan, or all for MakeMKV')
    parser.add_argument('--destination',default='',help='Local import folder or @node:library-root; otherwise remembered storage default')
    parser.add_argument('--release',type=int,help='MusicBrainz release number from scan (starting at 1)')
    parser.add_argument('--no-metadata',action='store_true',help='Skip the MusicBrainz lookup for CD capture')
    parser.add_argument('--json',action='store_true')
    args=parser.parse_args(argv);request=request_factory(args.node)
    try:
        if not args.action and sys.stdin.isatty() and sys.stdout.isatty():return workspace(request,read_key,hints)
        action=args.action or 'drives'
        if action=='watch':
            if not args.id:raise ValueError('watch requires a full job ID')
            if sys.stdin.isatty() and sys.stdout.isatty():return watch(args.id,request,read_key,hints)
            action='status'
        if action=='start':
            import media_storage
            result=capture(request,args.drive,args.kind,args.title,args.destination or media_storage.destination(args.kind),args.title_index,args.release,not args.no_metadata)
        else:
            if action in {'status','cancel','deliver'} and not args.id:raise ValueError(action+' requires a full job ID')
            result=request(action,{'drive':args.drive,'kind':args.kind,'id':args.id,'destination':args.destination})
        print(json.dumps(result,ensure_ascii=False,indent=2));return 0
    except (OSError,ValueError,RuntimeError) as exc:print('LOOK IMPORT · '+str(exc),file=sys.stderr);return 1
