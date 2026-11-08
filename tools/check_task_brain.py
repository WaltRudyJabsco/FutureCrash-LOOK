"""Live shared-brain checks. Disposable state; no paper or production Notes writes.

Real models and all three application entry points. The print transport is replaced
with a recorded receipt; Notes writes use a disposable JSON file for verification.
"""
import argparse
import contextlib
import io
import json
import sys
import tempfile
import time
from pathlib import Path
from check_memory_learning import load, ROOT
sys.path[:0]=[str(ROOT/'look'),str(ROOT/'core'),str(ROOT)]
import lo_engine, task_state, printing, notebook


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--surface',choices=['LO','Signal','Albert'])
    parser.add_argument('--followups-only',action='store_true')
    args=parser.parse_args()
    core=load('task_live_core',ROOT/'look/lk');lo_engine._CORE=core
    client=load('task_live_fabric_client',ROOT/'core/fabric_client.py')
    core._fabric_client_module=lambda:client
    signal=load('task_live_signal',ROOT/'signal-window/server.py')
    albert=load('task_live_albert',ROOT/'albert/server.py')
    signal.load_lo_engine=lambda *a:lo_engine
    albert._load_lo_engine=lambda:lo_engine
    with tempfile.TemporaryDirectory(prefix='look-task-proof-') as td:
        root=Path(td);old=core.STATE_DIR
        for key,value in list(vars(core).items()):
            if isinstance(value,Path) and value.is_relative_to(old):setattr(core,key,root/value.relative_to(old))
        core._queue_memory_exchange=lambda *a,**k:True
        core._queue_skill_feedback=lambda *a,**k:True
        core._save_recent_exchange=lambda *a,**k:None
        core._record_ai_stats=lambda *a,**k:None
        core._ai_foreground=lambda *a,**k:None
        core._start_memory_worker=lambda:None
        core._recent_context=lambda:''
        core._brain_context=lambda:''
        core._fabric_memory_sync=lambda:{}
        core._load_memory=lambda:core._empty_memory()
        import memory_store
        memory_store.default_path=lambda:root/'memory.json'
        sessions={};history=[];effects=[];plans=[]
        @contextlib.contextmanager
        def session(key):yield (sessions.setdefault(key,{}),lambda:None)
        task_state.session=session
        albert._session_history=lambda *a:list(history)
        albert._session_append=lambda *a:None
        printing.destinations=lambda:{'printers':[{'label':'Test Desk','name':'Test Desk'}]}
        printing.preferred_receipt=lambda *a:'Test Desk'
        def send(queue,text,**options):
            effects.append({'tool':'print_text','queue':queue,'text':text})
            return {'state':'queued','destination':queue,'id':'test-no-paper','receipt':{'job':'TEST-NO-PAPER'}}
        printing.quick_text=send
        def note(tool,values):
            if tool!='notebook_capture':raise RuntimeError('Unexpected note operation '+tool)
            effects.append({'tool':tool,**values});(root/'note.json').write_text(json.dumps(values))
            return json.dumps({'ok':True,'id':'disposable-note','text':values.get('text')})
        notebook.tool=note
        original_chat=core.ollama_chat
        def chat(**kwargs):
            kwargs['workspace_override']=td
            return original_chat(**kwargs)
        core.ollama_chat=chat
        original_file=core._run_filesystem_tool
        def file_tool(workspace,name,values,profile):
            result=original_file(workspace,name,values,profile)
            if name=='write_file':effects.append({'tool':name,**values})
            return result
        core._run_filesystem_tool=file_tool
        original=core._fabric_stream_chat
        allowed={'print_text','printers_list','notebook_capture','write_file'}
        def inference(payload_obj,**kwargs):
            accumulated=""
            for row in original(payload_obj,**kwargs):
                accumulated+=str(row.get("message",{}).get("content", ""))
                if row.get('done') and not payload_obj.get('tools'):print(json.dumps({'inference':accumulated, 'model':row.get('model')}),file=sys.stderr,flush=True)
                for call in row.get('message',{}).get('tool_calls',[]):
                    if call.get('function',{}).get('name') not in allowed:raise RuntimeError('Blocked unexpected test effect '+str(call))
                yield row
        core._fabric_stream_chat=inference
        def call(surface,prompt):
            start=time.monotonic();before=len(effects)
            if surface=='LO':
                events=lo_engine.EventCollector()
                with contextlib.redirect_stdout(io.StringIO()):
                    core.ollama_chat(initial_prompt=prompt,allow_start=True,access_profile='workspace',workspace_override=td,
                        one_shot=True,events=events,conversation_history=list(history),task_context=(sessions.setdefault('LO',{}),lambda:None))
                rows=events.rows
                answer=next((r['text'] for r in reversed(rows) if r['event']=='response'),'')
            elif surface=='Signal':answer,rows=signal.native_lo_chat('workspace',prompt,td,[],list(history),'proof')
            else:
                result=albert.cognition_json(prompt,session='proof');answer=result['text'];rows=result.get('events',[])
            interpretations=[r for r in rows if r.get('event')=='task_interpreted']
            errors=[r for r in rows if r.get('event') in {'error','task_interpretation_failed'}]
            print(json.dumps({'surface':surface,'prompt':prompt,'seconds':round(time.monotonic()-start,2),'answer':answer,'plan':interpretations,'errors':errors,'effects':effects[before:]}),flush=True)
            assert interpretations, 'No semantic interpretation: '+str(errors)
            history.extend([{'role':'user','content':prompt},{'role':'assistant','content':answer}])
            return answer,effects[before:]
        def check_followup(surface):
            history.clear();sessions.clear()
            answer,out=call(surface,'Please print a message on Test Desk.')
            assert not out and '?' in answer
            answer,out=call(surface,'The message is: Meet me at seven.')
            assert len(out)==1 and out[0]['tool']=='print_text' and 'seven' in out[0]['text'].lower()
        for surface in [args.surface] if args.surface else ['LO','Signal','Albert']:
            if args.followups_only:
                check_followup(surface)
                continue
            history.clear();sessions.clear()
            answer,out=call(surface,'Write a two-sentence briefing from this: Cedar launch is Monday; Jo owns testing. Just reply here, do not create a note.')
            assert not out and 'Cedar' in answer and 'Monday' in answer and 'Jo' in answer
            answer,out=call(surface,'Put that briefing on paper on Test Desk.')
            assert len(out)==1 and out[0]['tool']=='print_text' and 'Cedar' in out[0]['text']
            answer,out=call(surface,'Now save a new note called Garden Plan: peas in March, water twice weekly, label the rows.')
            assert len(out)==1 and out[0]['tool']=='notebook_capture'
            assert 'peas' in json.loads((root/'note.json').read_text())['text'].lower()
            answer,out=call(surface,'Instead of printing anything, just suggest a cheerful title for that garden plan.')
            assert not out and answer and 'incomplete' not in answer.casefold()
            history.clear();sessions.clear()
            (root/'briefing.txt').unlink(missing_ok=True)
            answer,out=call(surface,'Save a file named briefing.txt in the current workspace containing exactly: Cedar launches Monday. Jo owns testing.')
            assert (root/'briefing.txt').read_text().strip()=='Cedar launches Monday. Jo owns testing.'
            assert len(out)==1 and out[0]['tool']=='write_file'
            check_followup(surface)
        print('PASS: real model across requested surfaces; output and effect counts verified.')

if __name__=='__main__':main()
