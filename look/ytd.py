"""LOOK download client. Media bytes remain on the selected Fabric node."""
from __future__ import annotations
import argparse, json, sys, time
import urllib.parse, urllib.request, urllib.error
import fabric_files


def request(action=None,node='local',job=None,**payload):
    route='/v1/downloads'+('/'+str(job) if action is None and job else '')
    url=fabric_files.BASE+route+'?'+urllib.parse.urlencode({'target':node})
    data=None if action is None else json.dumps(dict(payload,action=action,**({'job':job} if job else {}))).encode()
    req=urllib.request.Request(url,data=data,headers={'Content-Type':'application/json'})
    try:
        with urllib.request.urlopen(req,timeout=65 if action=='find' else 20) as response: result=json.loads(response.read())
    except urllib.error.HTTPError as exc:
        try: message=json.loads(exc.read()).get('error')
        except (ValueError,AttributeError): message=str(exc)
        raise RuntimeError(message or str(exc)) from exc
    if not result.get('ok'): raise RuntimeError(result.get('error') or 'Download request failed')
    return result


def progress(row):
    info=row.get('progress') or {}; done=info.get('downloaded_bytes') or 0
    total=info.get('total_bytes') or info.get('total_bytes_estimate') or 0
    percent=f' · {done/total*100:.1f}%' if total else ''
    speed=f" · {info['speed']/1048576:.2f} MiB/s" if info.get('speed') else ''
    eta=f" · ETA {info['eta']:.0f}s" if info.get('eta') is not None else ''
    return f"{row['stage']} · {done/1048576:.2f} MiB{percent}{speed}{eta}"


def wait(job,node):
    last=''
    try:
        while True:
            row=request(node=node,job=job)['job']; line=progress(row)
            if line!=last: print(line,flush=True); last=line
            if row['stage'] in {'complete','failed','cancelled','expired'}: return row
            time.sleep(1)
    except KeyboardInterrupt:
        print(f'\nDownload continues. Resume: lk ytd status {job} --node {node} --wait')
        return None


def main(argv=None):
    parser=argparse.ArgumentParser(prog='lk ytd',description='Download on this node or a chosen Fabric node; downloads are permanent unless --holding is specified.')
    parser.add_argument('action',help='YouTube URL, find, jobs, status, keep, cancel, or index')
    parser.add_argument('value',nargs='*')
    parser.add_argument('--node',default='local')
    parser.add_argument('--to',dest='directory',help='Destination directory on the selected node, or @node:~/path')
    parser.add_argument('--holding',action='store_true',help='Opt in to 30-day retention; lk ytd keep makes the item permanent')
    parser.add_argument('--detach',action='store_true')
    parser.add_argument('--wait',action='store_true',dest='wait_for_job')
    parser.add_argument('--json',action='store_true',dest='as_json')
    args=parser.parse_intermixed_args(argv)
    try:
        destination=fabric_files.parse(args.directory) if args.directory else None
        if destination:
            if args.node!='local' and args.node.casefold()!=destination.node.casefold(): raise ValueError('--node and --to name different nodes')
            args.node=destination.node; args.directory=destination.path
        action=args.action; job=None
        if action=='find':
            result=request('find',node=args.node,query=' '.join(args.value))
            if args.as_json: print(json.dumps(result,indent=2)); return 0
            rows=result['results']
            for number,row in enumerate(rows,1): print(f"{number}. {row['title']} · {row.get('channel') or ''}\n   {row['url']}")
            if not rows: print('No matches.'); return 1
            if not sys.stdin.isatty(): return 0
            choice=input('Download number (Enter to cancel): ').strip()
            if not choice: return 0
            if not choice.isdigit() or not 1<=int(choice)<=len(rows): raise ValueError('Choose a listed number')
            result=request('download',node=args.node,url=rows[int(choice)-1]['url'],directory=args.directory,holding=args.holding)
            job=result['job']['id']
        elif action=='jobs': result=request(node=args.node)
        elif action in {'status','keep','cancel','index'}:
            if len(args.value)!=1: raise ValueError(f'Use lk ytd {action} JOB --node NODE')
            result=request(None if action=='status' else action,node=args.node,job=args.value[0],**({'directory':args.directory} if action=='keep' else {}))
            if action=='status' and args.wait_for_job: job=args.value[0]
        else:
            if args.value: raise ValueError('Quote the URL; only one video URL is accepted')
            result=request('download',node=args.node,url=action,directory=args.directory,holding=args.holding)
            job=result['job']['id']
        if job:
            if not args.as_json: print(f"DOWNLOAD · {result['node']} · job {job}")
            if not args.detach and not args.as_json:
                row=wait(job,args.node)
                if row is None: return 0
                result['job']=row
        if args.as_json: print(json.dumps(result,indent=2))
        elif 'jobs' in result:
            for row in result['jobs']: print(f"{row['id']} · {row['stage']} · {row.get('file') or row['url']}")
        else:
            row=result['job']; print(f"{row['stage']} · {row['id']}")
            if row.get('file'): print(f"@{result['node']}:{row['file']}")
            if row.get('catalog_state'): print(row['catalog_state'])
            if row.get('holding'): print('30-day holding · Keep: lk ytd keep '+row['id']+' --node '+args.node)
            if row.get('error'): print(row['error'],file=sys.stderr)
            if row['stage']=='failed': return 1
        return 0
    except (ValueError,RuntimeError,OSError) as exc:
        print(f'LOOK YTD · {exc}',file=sys.stderr); return 1


def tools():
    common={'node':{'type':'string','description':'Execution node, e.g. 3090. Default local.'}}
    definitions=[('video_search','Find five YouTube videos. Returns exact URLs; searching does not download.',{'query':{'type':'string'},**common},['query']),
        ('video_download','Start downloading one exact YouTube URL only when the user asks to download/save it. Returns a queued job, not a completed download. Files stay on the chosen node. Use holding only when the user explicitly asks for a temporary 30-day holding area.',{'url':{'type':'string'},'directory':{'type':'string'},'holding':{'type':'boolean'},**common},['url']),
        ('video_download_status','Check a download job on its execution node. Report complete only when the receipt says complete.',{'job':{'type':'string'},**common},['job'])]
    return [{'type':'function','function':{'name':name,'description':description,'parameters':{'type':'object','properties':properties,'required':required}}} for name,description,properties,required in definitions]


def tool(name,args):
    node=args.get('node') or 'local'
    if name=='video_search': result=request('find',node=node,query=args.get('query',''))
    elif name=='video_download':
        directory=args.get('directory'); dest=fabric_files.parse(directory) if directory else None
        if dest:
            if node!='local' and node.casefold()!=dest.node.casefold(): raise ValueError('Node and destination disagree')
            node=dest.node; directory=dest.path
        result=request('download',node=node,url=args.get('url',''),directory=directory,holding=args.get('holding') is True)
    else: result=request(node=node,job=args.get('job',''))
    return json.dumps(result,ensure_ascii=False)
