"""Live inference audit. Effects are mocked: no paper, no Notes changes.
Run from the repository root: python tools/check_tool_workflow.py --model MODEL
Weather reads the configured provider; inference uses the specified Ollama-compatible endpoint.
"""
import re
import sys,json,urllib.request,importlib.machinery,importlib.util,time,tempfile,argparse
from pathlib import Path
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--model',required=True)
parser.add_argument('--endpoint',default='http://127.0.0.1:11434/api/chat')
options=parser.parse_args()
root=Path(__file__).resolve().parents[1];sys.path[:0]=[str(root/'look'),str(root/'core')]
import lo_engine,printing,notebook,tool_workflow
loader=importlib.machinery.SourceFileLoader('audit_workflow_core',str(root/'look/lk'));spec=importlib.util.spec_from_loader(loader.name,loader);core=importlib.util.module_from_spec(spec);sys.modules[loader.name]=core;loader.exec_module(core);lo_engine._CORE=core
core._queue_memory_exchange=lambda *a,**k:False
core._save_recent_exchange=lambda *a,**k:None
core._record_ai_stats=lambda *a,**k:None
calls=[];envelopes=[]
def send(queue,text,exact_label=False):
 calls.append({'tool':'print_text','queue':queue,'text':text});return {'state':'queued','destination':queue,'id':'test-no-paper','receipt':{'job':'TEST-NO-PAPER'}}
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
cases=[('supplied_receipt','Print this as a compact Markdown receipt on Receipt Desk: Market list: eggs, rice, apples.'),('summary_note','Summarize this text and save the summary as a new note titled Garden Plan: Plant peas in March. Water them twice a week. Put labels on each row.'),('forecast','Will you print up a three-day forecast for Portland Oregon on Receipt Desk')]
results=[]
for name,prompt in cases:
 calls.clear();envelopes.clear();start=time.monotonic()
 try:
  with tempfile.TemporaryDirectory() as workspace:result=lo_engine.chat_once(prompt,workspace=workspace,profile='workspace')
  row={'case':name,'seconds':round(time.monotonic()-start,2),'calls':list(calls),'answer':result.get('text'),'satisfaction':result.get('satisfaction')}
 except Exception as e:row={'case':name,'error':str(e),'calls':list(calls)}
 results.append(row);print(json.dumps(row),flush=True)

failures=[]
for row in results:
 expected='notebook_capture' if row['case']=='summary_note' else 'print_text'
 effects=[c for c in row['calls'] if c['tool']==expected]
 if len(effects)!=1 or not (row.get('satisfaction') or {}).get('satisfied'):
  failures.append(row['case']);continue
 text=effects[0].get('text') or effects[0].get('args',{}).get('text','')
 tool_workflow.require_content(text,'Audit generated content')
 words={'summary_note':['peas','March','twice','labels'],
        'supplied_receipt':['eggs','rice','apples'],
        'forecast':['Portland','Open-Meteo']}[row['case']]
 if any(word.casefold() not in text.casefold() for word in words) or re.search(r'\[(?:summary|insert)[^]]*\]',text,re.I):
  failures.append(row['case'])
if failures:raise SystemExit('Workflow failed: '+', '.join(failures))
print('PASS: all three workflows produced content and exactly one successful mocked effect.')
