"""Live-model correction check through LO, Signal and Albert entry points.

Uses disposable memory/session files. Blocks effect tools and sends no paper.
The default exercises normal Fabric routing; --model selects a diagnostic model.
"""
import argparse
import contextlib
import importlib.machinery
import importlib.util
import io
import json
import sys
import tempfile
import urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'look'),str(ROOT/'core'),str(ROOT)]
import cognition, memory_store, memory_learning, lo_engine, task_state


def load(name,path):
    loader=importlib.machinery.SourceFileLoader(name,str(path))
    spec=importlib.util.spec_from_loader(name,loader)
    module=importlib.util.module_from_spec(spec);sys.modules[name]=module;loader.exec_module(module)
    return module


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model')
    parser.add_argument('--base',default='http://127.0.0.1:11434')
    args=parser.parse_args()
    core=load('memory_live_core',ROOT/'look/lk');lo_engine._CORE=core
    signal=load('memory_live_signal',ROOT/'signal-window/server.py')
    albert=load('memory_live_albert',ROOT/'albert/server.py')
    signal.load_lo_engine=lambda *a:lo_engine
    albert._load_lo_engine=lambda:lo_engine
    albert._session_history=lambda *a:[]
    albert._session_append=lambda *a:[]
    with tempfile.TemporaryDirectory(prefix='look-memory-proof-') as td:
        state=Path(td)
        old=core.STATE_DIR
        for key,value in list(vars(core).items()):
            if isinstance(value,Path) and value.is_relative_to(old):
                setattr(core,key,state/value.relative_to(old))
        store=memory_store.FabricMemory(state/'shared.json')
        core._fabric_memory_store=lambda:(store,'isolated-proof')
        memory_store.default_path=lambda:store.path
        core._fabric_memory_sync=lambda:{'ok':True,'failures':0}
        core._start_memory_worker=lambda:None
        core._ai_foreground=lambda *a:None
        core._record_ai_stats=lambda *a:None
        core._queue_skill_feedback=lambda *a:False
        # Skills are not part of this preference experiment.
        core._learn_from_exchange=lambda *a:False
        memory_calls=[]
        original_local=core._local_chat_once
        def local_call(*a,**k):
            result=original_local(*a,**k)
            memory_calls.append(result)
            return result
        core._local_chat_once=local_call
        original_chat=core.ollama_chat
        def isolated_chat(**kwargs):
            kwargs.setdefault('task_context',({},lambda:None))
            return original_chat(**kwargs)
        core.ollama_chat=isolated_chat
        core._recent_context=lambda:''
        core._brain_context=lambda:''
        @contextlib.contextmanager
        def session(*a):yield ({},lambda:None)
        task_state.session=session
        original=core._fabric_stream_chat
        seen=[]
        def inference(payload_obj,**kwargs):
            seen.append(payload_obj)
            if args.model:
                payload=dict(payload_obj,model=args.model,stream=False,think=False)
                payload['options']=dict(payload.get('options',{}),temperature=0,num_predict=500)
                req=urllib.request.Request(args.base+'/api/chat',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
                with urllib.request.urlopen(req,timeout=120) as response:rows=[json.load(response)]
            else:rows=original(payload_obj,**kwargs)
            for row in rows:
                if row.get("done"):
                    print(json.dumps({"model":row.get("model"),"tools":len(payload_obj.get("tools",[])),"reply":str(row.get("message",{}).get("content",""))[:160]}),file=sys.stderr,flush=True)
                if row.get('message',{}).get('tool_calls'):
                    raise RuntimeError('Unexpected tool call blocked in memory-only proof: '+str(row['message']['tool_calls']))
                yield row
        core._fabric_stream_chat=inference
        def call(surface,prompt):
            if surface=='LO':
                events=lo_engine.EventCollector()
                with contextlib.redirect_stdout(io.StringIO()):
                    core.ollama_chat(initial_prompt=prompt,allow_start=True,access_profile='workspace',
                        workspace_override=td,one_shot=True,events=events)
                answer=next((r['text'] for r in reversed(events.rows) if r['event']=='response'),'')
            elif surface=='Signal':answer=signal.native_lo_chat('workspace',prompt,td,[],[],None)[0]
            else:answer=albert.cognition_json(prompt,session='isolated-proof')['text']
            # Use the real durable queue and worker, not a seeded preference fixture.
            if args.model:
                for p in core._memory_job_files():
                    job=json.loads(p.read_text());job.update(base=args.base,model=args.model);p.write_text(json.dumps(job))
            rc=core._memory_worker()
            if rc or core._memory_job_files():
                raise RuntimeError('Memory processing failed: '+str(core._load_memory().get('last_worker_error'))+' synthetic outputs: '+repr(memory_calls[-3:]))
            print(json.dumps({'surface':surface,'prompt':prompt,'answer':answer,'records':len(store.load()['items'])}),flush=True)
            return answer
        call('LO','I prefer to be addressed as Captain AMBER. Please remember my preferred form of address.')
        assert any('AMBER' in r['text'] for r in store.load()['items']), 'initial preference was not captured'
        stale=store.public(False)['items']
        call('Signal','Correction: my preferred form of address is Captain COBALT, not Captain AMBER. Remember the new name for future conversations.')
        records=store.load()['items']
        assert any(r.get('revision',1)>1 and 'COBALT' in r['text'] for r in records), 'correction did not revise a record'
        # Exercise the real compressor with the captured current record, not invented text.
        compact=core._empty_memory()
        compact,_=core._add_durable(compact,records[0])
        compiler_model=args.model or core._active_ollama_model()
        compact,_=core._compile_memory(args.base,compiler_model,compact,force=True)
        summaries=json.dumps(compact.get('domain_summaries',{}))
        assert 'COBALT' in summaries and 'AMBER' not in summaries, 'compression lost the correction'
        print(json.dumps({'compression_preserved_correction':True}),flush=True)
        # Reopen storage and merge a stale replica to exercise durable state.
        snapshot=store.public(False)['items']
        for surface in ['Albert','LO','Signal']:
            store=memory_store.FabricMemory(state/(surface+'-replica.json'))
            store.merge(snapshot)
            store.merge(stale)
            # Do not let local candidate summaries carry the answer for this proof.
            core._save_memory(core._empty_memory())
            answer=call(surface,'What is my preferred form of address?')
            assert 'COBALT' in answer and 'AMBER' not in answer, surface+' did not apply correction'
            greeting=call(surface,'Please give me a friendly one-line greeting.')
            assert 'COBALT' in greeting and 'AMBER' not in greeting, surface+' did not personalize its greeting'
        print(json.dumps({'passed':True,'interfaces':['LO','Signal','Albert'],'model':args.model or 'normal Fabric routing'}))


if __name__=='__main__':main()
