"""Shared receipt archive, command cards and explicit reviewed print preparation."""
import argparse
import json
from pathlib import Path
import sys
import tempfile
import fabric_files


def owner(value=None):
    path=Path.home()/'.config/look/receipts.json'
    if value:
        import book_reader
        book_reader.write_json(path,{'node':value})
    try:return json.loads(path.read_text()).get('node') or 'local'
    except (OSError,ValueError):return 'local'

def request(action='list',**fields):
    node=fields.pop('node',None) or owner()
    return fabric_files.request('/v1/receipts',{'target':node},json.dumps(dict(action=action,**fields)).encode(),timeout=20)

def command_card(command):
    name=command.removeprefix('lk ').strip()
    path=Path(__file__).parent/'docs/command_help.json'
    help_text=json.loads(path.read_text()).get(name)
    if not help_text:raise ValueError('Unknown command; use a command name from lk commands')
    return request('create',title='Command / lk '+name,body=help_text,kind='command',source='Installed LOOK command reference')

def main(args):
    parser=argparse.ArgumentParser(prog='lk receipts',description='Digital receipt cards; print prepares a reviewed job, never sends paper automatically.')
    parser.add_argument('action',nargs='?',default='list',choices=['list','show','create','command','print'])
    parser.add_argument('value',nargs='?',default='')
    parser.add_argument('--body',help='Receipt text; use --body-file for a longer note or shopping list')
    parser.add_argument('--body-file',type=Path)
    parser.add_argument('--kind',choices=['note','feature','deployment'],default='note')
    parser.add_argument('--node',help='Remember the receipt archive owner')
    parser.add_argument('--printer',help='Physical printer nickname, e.g. Little Printer')
    parser.add_argument('--columns',type=int,default=32,help='Card width: 32 for a typical 58mm printer; 48 for 80mm')
    parser.add_argument('--json',action='store_true')
    value=parser.parse_args(args);owner(value.node)
    try:
        if value.action=='command':result=command_card(value.value)
        elif value.action=='create':
            if value.body_file and value.body:raise ValueError('Choose --body or --body-file')
            if value.body_file and value.body_file.stat().st_size>80000:raise ValueError('Receipt file is too large')
            body=value.body_file.read_text() if value.body_file else value.body
            result=request('create',title=value.value,body=body,kind=value.kind,source='User-authored card')
        else:result=request('list' if value.action=='list' else 'show',id=value.value,q=value.value,columns=value.columns)
        if value.action=='print':
            if not value.printer:raise ValueError('Choose --printer NAME from lk print list')
            import printing
            # The common pipeline resolves the physical printer and selects
            # document versus ESC/POS rendering from its actual profile.
            with tempfile.TemporaryDirectory(prefix='look-card-') as folder:
                path=Path(folder)/'receipt.txt';path.write_text(result['text'])
                plan=printing.prepare_file(value.printer,path)
            printing.display(plan);return 0
        if value.json:print(json.dumps(result,ensure_ascii=False,indent=2))
        elif 'receipt' in result:print(result['text'])
        else:
            print('LOOK RECEIPTS · '+str(result.get('node',owner())))
            for row in result['items']:print(row['id']+'  '+row['kind']+'  '+row['title'])
            if not result['items']:print('No cards yet. Try: lk receipts command ytr')
        return 0
    except (OSError,ValueError,RuntimeError) as exc:print('Receipts: '+str(exc));return 1

def tools():
    return [{'type':'function','function':{'name':'receipts_search','description':'Search saved Fabric receipt cards, including command references, deployment records and queued/downloaded items. Read-only; does not print.','parameters':{'type':'object','properties':{'query':{'type':'string'}},'additionalProperties':False}}}]
def run_tool(name,args):
    if name!='receipts_search':raise ValueError('Unknown receipt tool')
    return json.dumps(request('list',q=str(args.get('query') or '')))
