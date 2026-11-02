"""Fabric printing CLI and bounded assistant hooks. No model tool sends paper."""
import argparse
import base64
import json
from pathlib import Path
import sys
import fabric_files
from print_core import MAX_INPUT_BYTES


def _request(action='list',node='local',**fields):
    if action=='list' and node=='all':return fabric_files.request('/v1/print/fabric',timeout=60)
    return fabric_files.request('/v1/print',{'target':node},json.dumps(dict(action=action,**fields)).encode(),timeout=60)


def destinations():
    value=_request('list','all')
    if value.get('printers') and 'routes' not in value['printers'][0]:
        from print_destinations import consolidate
        value=dict(value,queues=value['printers'],printers=consolidate(value['printers']))
    return value


def request(action='list',node='local',**fields):
    if action=='list' and node=='all':return destinations()
    if node!='auto':return _request(action,node,**fields)
    from print_destinations import choose,route
    value=destinations();destination=choose(value,fields['queue'])
    if action in {'jobs','nickname'}:
        results=[]
        for candidate in destination['routes']:
            try:results.append(_request(action,candidate['node'],**dict(fields,queue=candidate['name'])))
            except (OSError,RuntimeError,ValueError) as error:results.append({'node':candidate['node'],'queue':candidate['name'],'error':str(error)})
        return {'printer':destination['label'],'view':action,'routes':results}
    selected=route(destination,value.get('local_node',''))
    # Choose before dispatch. Never fail over a write after it may have arrived.
    result=_request(action,selected['node'],**dict(fields,queue=selected['name']))
    return dict(result,destination=destination['label'])


def prepare(queue,node='auto',path=None,text=None,receipt=False,**options):
    if (path is None)==(text is None):raise ValueError('Choose exactly one file or text')
    if path is not None:
        source=Path(path).expanduser().resolve()
        if not source.is_file() or source.stat().st_size>MAX_INPUT_BYTES:raise ValueError('Choose a file up to 3 MiB')
        with source.open('rb') as stream:data=stream.read(MAX_INPUT_BYTES+1)
        title=source.name
        kind=('receipt-text' if source.suffix.casefold()=='.txt' else 'receipt-image') if receipt else 'document'
    else:
        data=str(text).encode('utf-8');title='LOOK receipt.txt' if receipt else 'LOOK text.txt'
        kind='receipt-text' if receipt else 'document'
    if not 0<len(data)<=MAX_INPUT_BYTES:raise ValueError('Print input must be 1 byte–3 MiB')
    result=request('prepare',node,queue=queue,data=base64.b64encode(data).decode(),filename=title,kind=kind,options_value=options)
    result['send_command']='lk print send '+result['id']+' --node '+result.get('node',node)+' --confirm'
    return result


def printable_file(path):
    source=Path(path).expanduser().resolve()
    if not source.is_file():raise ValueError('Choose one regular file to print; folders are not printable')
    if source.suffix.casefold() not in {'.pdf','.txt','.png','.jpg','.jpeg'}:raise ValueError('Print PDF, UTF-8 text, PNG or JPEG; export other documents/manuscripts to PDF first')
    if not 0<source.stat().st_size<=MAX_INPUT_BYTES:raise ValueError('Choose a nonempty file up to 3 MiB')
    return source


def prepare_file(queue,path,node='auto',receipt=None,**options):
    """All frontends share the same file validation and pinned destination route."""
    source=printable_file(path)
    if node=='auto':
        from print_destinations import choose,route
        value=destinations();destination=choose(value,queue)
        selected=route(destination,value.get('local_node',''));label=destination['label'];owner=selected['node']
    else:
        value=request('list',node)
        rows=[row for row in value.get('printers',[]) if row['name']==queue or row.get('profile',{}).get('label','').casefold()==queue.casefold()]
        if len(rows)!=1:raise ValueError('Choose an exact queue on this owner')
        selected=rows[0];owner=value.get('node',node);label=selected.get('profile',{}).get('label',selected['name'])
    is_receipt=selected.get('profile',{}).get('kind')=='escpos'
    if receipt is not None and receipt!=is_receipt:raise ValueError('Requested print format does not match the selected printer profile')
    if is_receipt and source.suffix.casefold()=='.pdf':raise ValueError('Choose a document printer for PDF; receipt printers accept text or raster images')
    result=prepare(selected['name'],owner,path=source,receipt=is_receipt,**options)
    return dict(result,destination=label)


def selected_file(path,ui):
    """Foreground file-manager handoff: choose, review, explicitly print, return."""
    from print_desk import pick
    from look_renderer import prompt_line
    plan=None
    try:
        source=printable_file(path)
        choice=pick(ui)
        if not choice:return 0
        plan=prepare_file(choice['id'],source)
        display(plan)
        answer,cancelled=prompt_line('Print '+source.name+' on '+plan['destination']+' via '+plan['node']+'? [p prints · Enter/Esc cancels] ')
        if cancelled or answer.strip().casefold()!='p':
            request('discard',plan['node'],ident=plan['id'],confirm=True)
            print('Print cancelled; the prepared content was discarded.')
            return 0
        result=request('send',plan['node'],ident=plan['id'],confirm=True)
        display(result)
        prompt_line('Enter returns to LOOK. ')
        return 0 if result.get('state')=='queued' else 1
    except KeyboardInterrupt:
        if plan:
            # Only discard an unsent draft. Never attempt a second submission.
            try:request('discard',plan['node'],ident=plan['id'],confirm=True)
            except (OSError,RuntimeError,ValueError):pass
        return 0
    except (OSError,ValueError,RuntimeError) as error:
        print('LOOK Print: '+str(error))
        if plan:print('Inspect this plan before retrying: '+plan['id']+' on '+plan['node'])
        prompt_line('Enter returns to LOOK. ')
        return 1


def parser():
    result=argparse.ArgumentParser(prog='lk print',description='Fabric printers and reviewed print plans; nothing prints during discovery/preparation.')
    result.add_argument('--json',action='store_true',help='Machine-readable result')
    sub=result.add_subparsers(dest='action')
    item=sub.add_parser('completion');item.add_argument('--confirm',action='store_true');item.add_argument('--node',default='local')
    for action in ['list','discover']:
        item=sub.add_parser(action);item.add_argument('--node',default='all' if action=='list' else 'local')
        if action=='list':item.add_argument('--queues',action='store_true',help='Show underlying owner/queue routes')
    for action in ['options','jobs']:
        item=sub.add_parser(action);item.add_argument('queue',nargs='?');item.add_argument('--node',default='auto')
    item=sub.add_parser('add');item.add_argument('queue');item.add_argument('--uri',required=True);item.add_argument('--driver',choices=['everywhere','raw'],default='everywhere');item.add_argument('--confirm',action='store_true');item.add_argument('--node',default='local')
    item=sub.add_parser('nickname');item.add_argument('queue',nargs='?');item.add_argument('label',nargs='?');item.add_argument('--confirm',action='store_true');item.add_argument('--node',default='auto')
    item=sub.add_parser('profile');item.add_argument('queue');item.add_argument('--kind',choices=['document','escpos'],required=True);item.add_argument('--width',type=int,default=384);item.add_argument('--columns',type=int,default=32);item.add_argument('--confirm',action='store_true');item.add_argument('--node',default='local')
    for action in ['file','text','receipt']:
        item=sub.add_parser(action);item.add_argument('content',nargs='?' if action=='receipt' else None);item.add_argument('--image');item.add_argument('--printer');item.add_argument('--node',default='auto');item.add_argument('--copies',type=int,default=1);item.add_argument('--pages');item.add_argument('--media');item.add_argument('--sides',choices=['one-sided','two-sided-long-edge','two-sided-short-edge'])
    for action in ['inspect','send','discard']:
        item=sub.add_parser(action);item.add_argument('ident');item.add_argument('--node',default='local')
        if action!='inspect':item.add_argument('--confirm',action='store_true')
    item=sub.add_parser('cancel');item.add_argument('queue');item.add_argument('job');item.add_argument('--confirm',action='store_true');item.add_argument('--node',default='local')
    for child in sub.choices.values():child.add_argument('--json',action='store_true',default=argparse.SUPPRESS)
    return result


def destination_label(row):
    label=row.get('profile',{}).get('label')
    return row['label'] if 'routes' in row else label+' ['+row['name']+']' if label and label!=row['name'] else row['name']


def display(result):
    if isinstance(result.get('options'),str) or isinstance(result.get('jobs'),str) or result.get('view')=='jobs':
        import print_details,shutil,terminal_style
        view='options' if 'options' in result else 'jobs'
        if 'jobs' in result:result={'routes':[result]}
        colors=terminal_style.list_colors() if sys.stdout.isatty() else None
        print('\n'.join(print_details.render(view,result,shutil.get_terminal_size((80,24)).columns,colors)))
        return
    if 'printers' in result:
        print('FABRIC PRINTERS')
        for row in result['printers']:print('  '+destination_label(row)+(' · '+str(row['route_count'])+' routes' if 'routes' in row else ' @ '+row.get('node','local')+' · '+row.get('profile',{}).get('kind','document')+' · '+row.get('status','')))
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


def main(args,ui=None):
    if not args and sys.stdin.isatty() and sys.stdout.isatty():
        from print_desk import desk
        return desk(ui)
    selected=parser().parse_args(args or ['list']);value=vars(selected);action=value.pop('action');node=value.pop('node','all');as_json=value.pop('json',False)
    try:
        if action in {'options','jobs','nickname'} and not value.get('queue') or action in {'file','text','receipt'} and not value.get('printer'):
            if not sys.stdin.isatty() or not sys.stdout.isatty():raise ValueError('Choose a printer; run lk print in a terminal or pass --printer/queue')
            from print_desk import pick
            choice=pick(ui,node=node)
            if not choice:return 0
            value['printer' if action in {'file','text','receipt'} else 'queue']=choice['id'] if node=='auto' else choice['routes'][0]['name']
        if action=='nickname' and not value.get('label'):
            if not sys.stdin.isatty() or not sys.stdout.isatty():raise ValueError('Provide a nickname, or use lk print in a terminal')
            from look_renderer import prompt_line
            value['label'],cancelled=prompt_line('Printer nickname: ')
            if cancelled:return 0
        queues=value.pop('queues',False)
        if action in {'file','text','receipt'}:
            content=value.pop('content');image=value.pop('image');queue=value.pop('printer')
            if image and (action!='receipt' or content):raise ValueError('--image is only for receipt images, without text')
            if action=='receipt' and not content and not image:raise ValueError('Choose receipt text or --image FILE')
            if content=='-' and action!='file':content=sys.stdin.buffer.read(MAX_INPUT_BYTES+1).decode('utf-8')
            options={k:v for k,v in value.items() if v is not None}
            result=prepare_file(queue,content,node,**options) if action=='file' else prepare(queue,node,path=image,text=None if image else content,receipt=action=='receipt',**options)
        else:result=request(action or 'list',node,**value)
        if queues:result=dict(result,printers=result.get('queues',[]))
        if as_json:print(json.dumps(result,ensure_ascii=False,indent=2))
        else:display(result)
        return 0
    except (OSError,ValueError,RuntimeError) as error:print('LOOK Print: '+str(error));return 1


def tools():
    fields={'node':{'type':'string','description':'Optional exact owner; default auto selects an enabled route'},'queue':{'type':'string','description':'Stable physical printer ID or unique friendly name from discovery; an exact queue works with an explicit owner'}}
    return [
        {'type':'function','function':{'name':'printers_list','description':'List physical printers once across the trusted Fabric, with stable ID, friendly name and underlying queue routes. No setup or printing.','parameters':{'type':'object','properties':{},'additionalProperties':False}}},
        {'type':'function','function':{'name':'printer_inspect','description':'Inspect printer options or jobs on an exact owner/queue.','parameters':{'type':'object','properties':dict(fields,view={'type':'string','enum':['options','jobs']}),'required':['queue'],'additionalProperties':False}}},
        {'type':'function','function':{'name':'print_prepare','description':'Prepare a text/document/receipt job for user review, NEVER send paper. Return immutable plan, options and confirmation command. Choose a physical printer from discovery; automatic routing hides its underlying queues. Export DOCX/manuscripts to PDF before preparing.','parameters':{'type':'object','properties':dict(fields,path={'type':'string'},text={'type':'string'},receipt={'type':'boolean','description':'True for a configured ESC/POS receipt destination; false for document printers'},copies={'type':'integer','minimum':1,'maximum':20},pages={'type':'string'},media={'type':'string'},sides={'type':'string','enum':['one-sided','two-sided-long-edge','two-sided-short-edge']}),'required':['queue'],'additionalProperties':False}}}]


def run_tool(tool,args,workspace):
    value=dict(args)
    if tool=='printers_list':return json.dumps(request('list','all'))
    if tool=='printer_inspect':
        if set(value)-{'view','node','queue'}:raise ValueError('Printer inspection accepts only owner, queue and options/jobs view')
        view=value.pop('view','options')
        if view not in {'options','jobs'}:raise ValueError('Printer inspection is read-only: choose options or jobs')
        return json.dumps(request(view,value.pop('node','auto'),**value))
    if tool!='print_prepare':raise ValueError('Unknown print tool')
    if value.get('path'):
        path=Path(value['path']).expanduser()
        path=(Path(workspace)/path).resolve() if not path.is_absolute() else path.resolve()
        if not path.is_relative_to(Path(workspace).resolve()):raise ValueError('Print files must be inside the current workspace; explicitly copy/export the document there first')
        value['path']=str(path)
        return json.dumps(prepare_file(**value))
    return json.dumps(prepare(**value))
