"""Live shared-brain checks. Disposable state; no paper or production Notes writes.

Real models and all three application entry points. The print transport is replaced
with a recorded receipt; Notes use the real store in a disposable directory.
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
    parser.add_argument('--dialogue',action='store_true',help='Exercise conversational choices and proposed actions')
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
        original_note=notebook.tool
        store=notebook.Notebook(root/'notes',origin='task-proof')
        notebook.Notebook=lambda:store
        notebook.nudge_sync=lambda:None
        def note(tool,values):
            if tool!='notebook_capture':raise RuntimeError('Unexpected note operation '+tool)
            assert values.get('target','all') in {'all','local'}, 'Unexpected note delivery target: '+str(values)
            result=original_note(tool,values)
            effects.append({'tool':tool,**values});(root/'note.json').write_text(json.dumps(values))
            assert any('water' in row.get('body','').lower() or values['text'].splitlines()[0].lstrip('# ') == row['title'] for row in store.list(include_done=True))
            return result
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
        allowed={'print_text','printers_list','notebook_capture','write_file','museum_search'}
        def inference(payload_obj,**kwargs):
            accumulated=""
            for row in original(payload_obj,**kwargs):
                accumulated+=str(row.get("message",{}).get("content", ""))
                if row.get('done') and not payload_obj.get('tools'):print(json.dumps({'inference':accumulated, 'model':row.get('model')}),file=sys.stderr,flush=True)
                for call in row.get('message',{}).get('tool_calls',[]):
                    if call.get('function',{}).get('name') not in allowed:raise RuntimeError('Blocked unexpected test effect '+str(call))
                yield row
        core._fabric_stream_chat=inference
        last_rows=[]
        def call(surface,prompt):
            nonlocal last_rows
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
                result=albert.cognition_json(prompt,session='proof');answer=result['text'];rows=result.get('lo_events',[])
            last_rows=rows
            interpretations=[r for r in rows if r.get('event')=='task_interpreted']
            errors=[r for r in rows if r.get('event') in {'error','task_interpretation_failed'}]
            print(json.dumps({'surface':surface,'prompt':prompt,'seconds':round(time.monotonic()-start,2),'answer':answer,'plan':interpretations,'errors':errors,'calls':[r.get('tool') for r in rows if r.get('event')=='tool_start'],'effects':effects[before:]}),flush=True)
            assert interpretations, 'No semantic interpretation: '+str(errors)
            history.extend([{'role':'user','content':prompt},{'role':'assistant','content':answer}])
            return answer,effects[before:]
        def check_followup(surface):
            history.clear();sessions.clear()
            answer,out=call(surface,'Please print a message on Test Desk.')
            assert not out and '?' in answer
            answer,out=call(surface,'The message is: Meet me at seven.')
            assert len(out)==1 and out[0]['tool']=='print_text' and 'seven' in out[0]['text'].lower()
        def check_dialogue(surface):
            history.clear();sessions.clear()
            answer,out=call(surface,'Find a Renoir in our Museum and tell me a little about it.')
            assert not out and 'Renoir' in answer and 'which one' not in answer.lower(), answer
            answer,out=call(surface,'What unifies his work?')
            assert not out and len(answer)>100 and not any(r.get('event')=='tool_start' for r in last_rows), answer
            # Reproduce the user's actual offered-choice transcript, independent of
            # whether this model volunteers a menu on its first answer.
            history.clear();sessions.clear()
            history.extend([{'role':'user','content':'Tell me about one of these paintings.'},
                {'role':'assistant','content':'Which interests you? 1. Acrobats at the Cirque Fernando by Renoir (1879). 2. By the Seashore by Renoir (1883).'}])
            answer,out=call(surface,'1')
            assert not out and ('Acrobats' in answer or 'Fernando' in answer) and len(answer)>200 and 'print' not in answer.lower(), answer
            history.clear();sessions.clear()
            answer,out=call(surface,'Here is my checklist: pack water, take a hat. Put it somewhere useful, but I am not sure whether I want paper or a saved note.')
            assert not out and '?' in answer, answer
            assert any(v.get('brain_proposal') for v in sessions.values()), sessions
            answer,out=call(surface,'What would that do?')
            assert not out and answer, answer
            answer,out=call(surface,'Save it as a note instead. Call it Walk Kit.')
            assert len(out)==1 and out[0]['tool']=='notebook_capture' and 'water' in out[0].get('text','').lower(),out
            history.clear();sessions.clear()
            answer,out=call(surface,'Suggest saving a note called Lunch Plan containing soup and bread. Ask before you save it.')
            assert not out and '?' in answer, answer
            answer,out=call(surface,'Yes, do that.')
            assert len(out)==1 and out[0]['tool']=='notebook_capture' and 'soup' in out[0].get('text','').lower(),out
            answer,out=call(surface,'Thanks, yes.')
            assert not out,out
            history.clear();sessions.clear()
            answer,out=call(surface,'Suggest printing the message Hello on Test Desk, but ask me before doing it.')
            assert not out and '?' in answer, answer
            answer,out=call(surface,'No, forget it. Just tell me a short joke.')
            assert not out and answer,answer
            assert not any(v.get('brain_proposal') for v in sessions.values()),sessions
        for surface in [args.surface] if args.surface else ['LO','Signal','Albert']:
            if args.dialogue:
                check_dialogue(surface)
                continue
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
