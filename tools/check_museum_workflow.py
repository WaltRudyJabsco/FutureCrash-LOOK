"""Live inference audit. Effects are mocked: no paper, no Notes changes.
Run from the repository root: python tools/check_museum_workflow.py --model MODEL
Museum reads the configured catalog owner; inference uses the specified Ollama-compatible endpoint.
"""
import re
import sys,json,urllib.request,importlib.machinery,importlib.util,time,tempfile,argparse
from pathlib import Path
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--model',required=True)
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
allowed={'print_text','print_prepare','printers_list','printer_inspect','notebook_capture','notebook_read','notebook_list','notebook_search','notebook_update','weather'}
def inference(payload_obj,**kwargs):
 payload=dict(payload_obj,model=options.model,stream=False,think=False)
 payload['options']=dict(payload.get('options',{}),temperature=0,num_predict=700)
 envelopes.append({'tools':[x['function']['name'] for x in payload.get('tools',[])],'messages':payload['messages']})
 req=urllib.request.Request(options.endpoint,data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
 with urllib.request.urlopen(req,timeout=60) as response:out=json.load(response)
 for call in out.get('message',{}).get('tool_calls',[]):
  if call.get('function',{}).get('name') not in allowed:raise RuntimeError('Blocked unexpected test effect '+str(call))
 out['done']=True;yield out
core._fabric_stream_chat=inference

allowed.update({'museum_search','print_artwork'})
def artwork(queue,artwork_id):
 from museum_desk import Client,preference
 row=next(r for r in Client(preference()).snapshot()['items'] if r['id']==artwork_id)
 calls.append({'tool':'print_artwork','queue':queue,'id':artwork_id,'artist':row.get('artist'),'title':row.get('title')})
 return {'state':'queued','id':'mock-art-job','destination':queue}
printing.quick_artwork=artwork
for prompt in ['Print a random museum image on Receipt Desk','Print a Renoir image from the museum on Receipt Desk','Print something by Renoir']:
 calls.clear()
 try:
  with tempfile.TemporaryDirectory() as workspace:result=lo_engine.chat_once(prompt,workspace=workspace,profile='workspace')
 except Exception:
  print('CALLS',calls)
  print('TOOLS',envelopes[-1]['tools'])
  for m in envelopes[-1]['messages']:
   if m.get('role')=='tool' or m.get('tool_calls'):print(str(m)[:1000])
  raise
 print(json.dumps({'prompt':prompt,'calls':calls,'text':result.get('text'),'satisfaction':result.get('satisfaction')}),flush=True)
 assert len(calls)==1 and calls[0]['tool']=='print_artwork'
 assert result.get('satisfaction',{}).get('satisfied')
 if 'Renoir' in prompt:assert 'renoir' in calls[0]['artist'].casefold()
print('PASS: random and artist requests reach exactly one mocked artwork print each.')
