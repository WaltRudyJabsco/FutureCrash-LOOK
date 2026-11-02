"""Fabric printing CLI and bounded assistant hooks. No model tool sends paper."""
import argparse
import base64
import json
from pathlib import Path
import sys
import fabric_files
from print_core import MAX_INPUT_BYTES


def request(action='list',node='local',**fields):
    if action=='list' and node=='all':return fabric_files.request('/v1/print/fabric',timeout=60)
    return fabric_files.request('/v1/print',{'target':node},json.dumps(dict(action=action,**fields)).encode(),timeout=60)


def prepare(queue,node='local',path=None,text=None,receipt=False,**options):
    if (path is None)==(text is None):raise ValueError('Choose exactly one file or text')
    if path is not None:
        source=Path(path).expanduser().resolve()
        if not source.is_file() or source.stat().st_size>MAX_INPUT_BYTES:raise ValueError('Choose a file up to 3 MiB')
        with source.open('rb') as stream:data=stream.read(MAX_INPUT_BYTES+1)
        title=source.name
        kind='receipt-image' if receipt else 'document'
    else:
        data=str(text).encode('utf-8');title='LOOK receipt.txt' if receipt else 'LOOK text.txt'
        kind='receipt-text' if receipt else 'document'
    if not 0<len(data)<=MAX_INPUT_BYTES:raise ValueError('Print input must be 1 byte–3 MiB')
    result=request('prepare',node,queue=queue,data=base64.b64encode(data).decode(),filename=title,kind=kind,options_value=options)
    result['send_command']='lk print send '+result['id']+' --node '+node+' --confirm'
    return result


def parser():
    result=argparse.ArgumentParser(prog='lk print',description='Fabric printers and reviewed print plans; nothing prints during discovery/preparation.')
    result.add_argument('--json',action='store_true',help='Machine-readable result')
    sub=result.add_subparsers(dest='action')
    for action in ['list','discover']:
        item=sub.add_parser(action);item.add_argument('--node',default='all' if action=='list' else 'local')
    for action in ['options','jobs']:
        item=sub.add_parser(action);item.add_argument('queue');item.add_argument('--node',default='local')
    item=sub.add_parser('add');item.add_argument('queue');item.add_argument('--uri',required=True);item.add_argument('--driver',choices=['everywhere','raw'],default='everywhere');item.add_argument('--confirm',action='store_true');item.add_argument('--node',default='local')
    item=sub.add_parser('nickname');item.add_argument('queue');item.add_argument('label');item.add_argument('--confirm',action='store_true');item.add_argument('--node',default='local')
    item=sub.add_parser('profile');item.add_argument('queue');item.add_argument('--kind',choices=['document','escpos'],required=True);item.add_argument('--width',type=int,default=384);item.add_argument('--columns',type=int,default=32);item.add_argument('--confirm',action='store_true');item.add_argument('--node',default='local')
    for action in ['file','text','receipt']:
        item=sub.add_parser(action);item.add_argument('content',nargs='?' if action=='receipt' else None);item.add_argument('--image');item.add_argument('--printer',required=True);item.add_argument('--node',default='local');item.add_argument('--copies',type=int,default=1);item.add_argument('--pages');item.add_argument('--media');item.add_argument('--sides',choices=['one-sided','two-sided-long-edge','two-sided-short-edge'])
    for action in ['inspect','send','discard']:
        item=sub.add_parser(action);item.add_argument('ident');item.add_argument('--node',default='local')
        if action!='inspect':item.add_argument('--confirm',action='store_true')
    item=sub.add_parser('cancel');item.add_argument('queue');item.add_argument('job');item.add_argument('--confirm',action='store_true');item.add_argument('--node',default='local')
    for child in sub.choices.values():child.add_argument('--json',action='store_true',default=argparse.SUPPRESS)
    return result


def destination_label(row):
    label=row.get('profile',{}).get('label')
    return label+' ['+row['name']+']' if label and label!=row['name'] else row['name']


def display(result):
    if 'printers' in result:
        print('FABRIC PRINTERS')
        for row in result['printers']:print('  '+destination_label(row)+' @ '+row.get('node','local')+' · '+row.get('profile',{}).get('kind','document')+' · '+row.get('status',''))
        if not result['printers']:print('No configured queues visible. Run lk print discover --node OWNER or open that computer’s printer settings.')
        for error in result.get('errors',[]):print('Unavailable: '+str(error.get('node','owner'))+' · '+str(error.get('error','')))
    elif 'id' in result and 'state' in result:
        print('PRINT PLAN · '+result['state']+' · '+result.get('title',''))
        print('Printer: '+result['queue']+' @ '+result.get('node','local')+' · '+result['kind']+' · '+str(result['bytes'])+' bytes')
        print('Options: '+', '.join(k+'='+str(v) for k,v in result['options'].items()))
        print(result['note'])
        if result.get('text_preview'):print('Text preview'+(' (truncated)' if result.get('preview_truncated') else '')+':\n'+result['text_preview'])
        if result.get('receipt'):print(json.dumps(result['receipt'],ensure_ascii=False))
        print(result.get('send_command','Plan: '+result['id']))
    else:
        for key,value in result.items():
            if key not in {'ok','node'}:print(key+': '+(json.dumps(value,ensure_ascii=False) if isinstance(value,(dict,list)) else str(value)))


def main(args):
    selected=parser().parse_args(args or ['list']);value=vars(selected);action=value.pop('action');node=value.pop('node','all');as_json=value.pop('json',False)
    try:
        if action in {'file','text','receipt'}:
            content=value.pop('content');image=value.pop('image');queue=value.pop('printer')
            if image and (action!='receipt' or content):raise ValueError('--image is only for receipt images, without text')
            if action=='receipt' and not content and not image:raise ValueError('Choose receipt text or --image FILE')
            if content=='-' and action!='file':content=sys.stdin.buffer.read(MAX_INPUT_BYTES+1).decode('utf-8')
            options={k:v for k,v in value.items() if v is not None}
            result=prepare(queue,node,path=content if action=='file' else image,text=None if action=='file' or image else content,receipt=action=='receipt',**options)
        else:result=request(action or 'list',node,**value)
        if as_json:print(json.dumps(result,ensure_ascii=False,indent=2))
        else:display(result)
        return 0
    except (OSError,ValueError,RuntimeError) as error:print('LOOK Print: '+str(error));return 1


def tools():
    fields={'node':{'type':'string','description':'Exact owner from printer discovery; default local'},'queue':{'type':'string','description':'Exact queue name or unique nickname from discovery'}}
    return [
        {'type':'function','function':{'name':'printers_list','description':'List configured printers across the trusted Fabric, with queue, owner and document/receipt profile. No setup or printing.','parameters':{'type':'object','properties':{},'additionalProperties':False}}},
        {'type':'function','function':{'name':'printer_inspect','description':'Inspect printer options or jobs on an exact owner/queue.','parameters':{'type':'object','properties':dict(fields,view={'type':'string','enum':['options','jobs']}),'required':['queue'],'additionalProperties':False}}},
        {'type':'function','function':{'name':'print_prepare','description':'Prepare a text/document/receipt job for user review, NEVER send paper. Return immutable plan, options and confirmation command. Ask for an exact printer/owner first. Export DOCX/manuscripts to PDF before preparing.','parameters':{'type':'object','properties':dict(fields,path={'type':'string'},text={'type':'string'},receipt={'type':'boolean','description':'True for a configured ESC/POS receipt destination; false for document printers'},copies={'type':'integer','minimum':1,'maximum':20},pages={'type':'string'},media={'type':'string'},sides={'type':'string','enum':['one-sided','two-sided-long-edge','two-sided-short-edge']}),'required':['queue'],'additionalProperties':False}}}]


def run_tool(tool,args,workspace):
    value=dict(args)
    if tool=='printers_list':return json.dumps(request('list','all'))
    if tool=='printer_inspect':
        if set(value)-{'view','node','queue'}:raise ValueError('Printer inspection accepts only owner, queue and options/jobs view')
        view=value.pop('view','options')
        if view not in {'options','jobs'}:raise ValueError('Printer inspection is read-only: choose options or jobs')
        return json.dumps(request(view,value.pop('node','local'),**value))
    if tool!='print_prepare':raise ValueError('Unknown print tool')
    if value.get('path'):
        path=Path(value['path']).expanduser()
        path=(Path(workspace)/path).resolve() if not path.is_absolute() else path.resolve()
        if not path.is_relative_to(Path(workspace).resolve()):raise ValueError('Print files must be inside the current workspace; explicitly copy/export the document there first')
        value['path']=str(path)
    return json.dumps(prepare(**value))
