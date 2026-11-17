"""Fabric Theater command line and assistant edge."""
import argparse
import json
from pathlib import Path
import subprocess
import shutil
import sys
import urllib.parse
import urllib.request
import urllib.error


def request(value=None,node='local'):
    url='http://127.0.0.1:7332/v1/theater?'+urllib.parse.urlencode({'target':node})
    req=urllib.request.Request(url,data=json.dumps(value or {'action':'status'}).encode(),headers={'Content-Type':'application/json'})
    try:
        with urllib.request.urlopen(req,timeout=50) as response:return json.load(response)
    except urllib.error.HTTPError as exc:
        try:message=json.load(exc).get('error')
        except ValueError:message='Theater host unavailable'
        raise ValueError(message) from exc


def main(argv=None,ui=None):
    parser=argparse.ArgumentParser(prog='lk theater',description='Movie tickets and shared browser showings. Select the node that owns the media.')
    parser.add_argument('--node');parser.add_argument('--json',action='store_true')
    sub=parser.add_subparsers(dest='command')
    sub.add_parser('status');sub.add_parser('menu')
    item=sub.add_parser('search');item.add_argument('query',nargs='*')
    item=sub.add_parser('setup');item.add_argument('--url',required=True)
    sub.add_parser('qr-setup')
    item=sub.add_parser('ticket');item.add_argument('media',nargs='?');item.add_argument('--channel',action='store_true');item.add_argument('--hours',type=float,default=24);item.add_argument('--qr',type=Path)
    item=sub.add_parser('show');item.add_argument('media')
    item=sub.add_parser('revoke');item.add_argument('id')
    for command in ['pause','resume','stop']:sub.add_parser(command)
    item=sub.add_parser('seek');item.add_argument('position',type=float)
    item=sub.add_parser('channel');item.add_argument('access',choices=['open','ticketed'])
    args=parser.parse_args(argv)
    try:
        if args.command=='menu' or (args.command is None and not args.json and sys.stdin.isatty() and sys.stdout.isatty()):
            if ui is None or not sys.stdin.isatty():raise ValueError('Open the terminal menu through lk theater')
            from theater_terminal import Desk
            return Desk(ui,args.node).run()
        args.node=args.node or 'local'
        if args.command=='qr-setup':
            if args.node!='local':raise ValueError('Run qr-setup directly on the Theater host')
            dest=Path.home()/'.local/share/future-crash-look/theater-python'
            candidates=[sys.executable,shutil.which('python3'),'/opt/homebrew/bin/python3','/usr/local/bin/python3','/home/linuxbrew/.linuxbrew/bin/python3']
            python=next((p for p in candidates if p and Path(p).is_file() and subprocess.run([p,'-m','pip','--version'],capture_output=True).returncode==0),None)
            if python is None:raise ValueError('Install Python with pip to set up Theater QR support')
            subprocess.run([python,'-m','pip','install','--target',str(dest),'qrcode[png]>=8,<9'],check=True)
            return 0
        value={'action':args.command or 'status'}
        if args.command=='search':value['query']=' '.join(args.query)
        if args.command=='setup':value={'action':'configure','url':args.url}
        if args.command=='ticket':value.update(media=args.media,scope='channel' if args.channel else 'movie',hours=args.hours)
        if args.command=='show':value['media']=args.media
        if args.command=='revoke':value['id']=args.id
        if args.command=='seek':value['position']=args.position
        if args.command=='channel':value={'action':'access','public':args.access=='open'}
        result=request(value,args.node)
        if args.command=='ticket' and args.qr:
            import base64
            qr=request({'action':'qr','code':result['code']},args.node)
            with args.qr.expanduser().open('xb') as stream:stream.write(base64.b64decode(qr['png']))
            result['qr_file']=str(args.qr)
        if args.json:print(json.dumps(result,indent=2));return 0
        if args.command=='search':
            for row in result['items']:print(row['id']+' · '+row['title'])
        elif args.command=='ticket':
            print(result['title']+'\n'+result['url']+'\nCode '+result['code']+' · valid '+str(args.hours)+' hours')
            if result.get('qr_file'):print('QR saved to '+result['qr_file'])
        else:print(json.dumps(result,indent=2))
        return 0
    except (ValueError,OSError,subprocess.CalledProcessError) as exc:
        print('Theater: '+str(exc));return 1


def tools():
    return [
        {'type':'function','function':{'name':'theater_lookup','description':'Inspect Fabric Theater showing/tickets or search media on its host. Use a trusted node name for the media owner. Returns movie IDs for showing or ticket issuance.','parameters':{'type':'object','properties':{'node':{'type':'string'},'query':{'type':'string'}}}}},
        {'type':'function','function':{'name':'theater_control','description':'When requested, start/pause/resume/seek/stop a shared Theater showing, issue an expiring movie/channel ticket, or revoke a ticket. Use media IDs from theater_lookup. Ticket links grant viewing access to their holders.','parameters':{'type':'object','properties':{'node':{'type':'string'},'action':{'type':'string','enum':['show','pause','resume','seek','stop','ticket','revoke']},'media':{'type':'string'},'scope':{'type':'string','enum':['movie','channel']},'hours':{'type':'number'},'position':{'type':'number'},'id':{'type':'string'}},'required':['action']}}}]


def run_tool(name,args):
    value=dict(args);node=value.pop('node','local')
    if name=='theater_lookup':value={'action':'search','query':value['query']} if 'query' in value else {'action':'status'}
    elif value.get('action') not in {'show','pause','resume','seek','stop','ticket','revoke'}:raise ValueError('Use Theater settings for public access and setup')
    return json.dumps(request(value,node))
