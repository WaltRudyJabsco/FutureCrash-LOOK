"""Live inference audit. Effects are mocked: no paper, no Notes changes.
Run from the repository root: python tools/check_terminal_workflow.py
Uses normal Fabric inference settings and the actual terminal loop. Weather and Museum reads are real; print submissions are intercepted.
"""
import re
import sys,json,urllib.request,importlib.machinery,importlib.util,time,tempfile,argparse
from pathlib import Path
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--model',help='Unused compatibility option; normal Fabric chooses the model')
parser.add_argument('--endpoint',default='http://127.0.0.1:11434/api/chat')
options=parser.parse_args()
root=Path(__file__).resolve().parents[1];sys.path[:0]=[str(root/'look'),str(root/'core')]
import cognition
import lo_engine,printing,notebook,tool_workflow
loader=importlib.machinery.SourceFileLoader('audit_workflow_core',str(root/'look/lk'));spec=importlib.util.spec_from_loader(loader.name,loader);core=importlib.util.module_from_spec(spec);sys.modules[loader.name]=core;loader.exec_module(core);lo_engine._CORE=core
core._queue_memory_exchange=lambda *a,**k:False
core._save_recent_exchange=lambda *a,**k:None
core._record_ai_stats=lambda *a,**k:None
calls=[];envelopes=[]
def send(queue,text,exact_label=False,**options):
 calls.append({'tool':'print_text','queue':queue,'text':text,**options});return {'state':'queued','destination':queue,'id':'test-no-paper','receipt':{'job':'TEST-NO-PAPER'}}
printing.quick_text=send
printing.preferred_receipt=lambda prompt='':'Receipt Desk'
printing.destinations=lambda:{'printers':[{'label':'Receipt Desk','name':'Receipt Desk','routes':[{'name':'receipt','node':'fixture','profile':{'kind':'escpos','preferred_receipt':True}}]}]}
printing.request=lambda action,node='local',**kw: printing.destinations() if action=='list' else {'state':'prepared','id':'fixture','node':'fixture'}
def note(tool,args):
 calls.append({'tool':tool,'args':args})
 if tool=='notebook_capture':return json.dumps({'ok':True,'id':'test-note','title':args.get('title'),'body':args.get('body',args.get('text',''))})
 if tool=='notebook_update':return json.dumps({'ok':True,'id':'test-note','revision':2})
 return json.dumps({'notes':[]})
notebook.tool=note
original_inference=core._fabric_stream_chat
def routed(payload_obj,**kwargs):
 envelopes.append(payload_obj)
 yield from original_inference(payload_obj,**kwargs)
core._fabric_stream_chat=routed


from museum_desk import Client,preference
printing.quick_artwork=lambda queue,artwork_id: (calls.append({'tool':'print_artwork','queue':queue,'id':artwork_id}) or {'state':'queued','id':'test-art','destination':queue})
answers=iter(['print something by Renoir on Receipt Desk','how about printing a three day forcast'])
def read_input():
 try:return next(answers)
 except StopIteration:raise EOFError
core._lo_read_input=read_input
old_transaction=core._tool_transaction
def transaction(name,args,fn):
 if name not in {'print_text','print_artwork','museum_search','printers_list','printer_inspect','weather'}:raise RuntimeError('Unexpected audit effect: '+name)
 return old_transaction(name,args,fn)
core._tool_transaction=transaction
core._run_command_tool=lambda *a,**k: (_ for _ in ()).throw(RuntimeError('No shell commands permitted in audit'))
events=lo_engine.EventCollector()
with tempfile.TemporaryDirectory() as workspace:
 core.ollama_chat(initial_prompt='print a three-day forecast with a weather picture on Receipt Desk',access_profile='power',workspace_override=workspace,events=events,one_shot=False)
print(json.dumps({'calls':calls,'responses':[e for e in events.rows if e['event']=='response']}),flush=True)
assert [c['tool'] for c in calls]==['print_text','print_artwork','print_text']
assert calls[0].get('illustration')
print('PASS terminal sequence, normal Fabric routing, no paper')
