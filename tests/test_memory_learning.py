import importlib.machinery
import importlib.util
import json
import sys
from pathlib import Path

import pytest
import memory_learning as learning
from memory_store import FabricMemory
import tool_workflow

ROOT=Path(__file__).resolve().parents[1]
loader=importlib.machinery.SourceFileLoader('lk_memory_repair',str(ROOT/'look/lk'))
spec=importlib.util.spec_from_loader(loader.name,loader)
lk=importlib.util.module_from_spec(spec);sys.modules[loader.name]=lk;loader.exec_module(lk)


def test_wrapped_candidate_and_failure_diagnostics(monkeypatch):
    assert learning.parse_candidate('72|I prefer readable\nreceipt text')[0]==(72,'I prefer readable receipt text')
    assert learning.parse_candidate('72|one\n80|another')[1]=='parse_error'
    d={}
    monkeypatch.setattr(lk,'_local_chat_once',lambda *a,**k:(_ for _ in ()).throw(TimeoutError()))
    assert lk._extract_memory_candidate('','', 'preference','',d) is None
    assert d=={'status':'error','error_type':'TimeoutError'}


def test_correction_survives_replication_restart_and_paraphrase(tmp_path):
    a=FabricMemory(tmp_path/'a.json');b=FabricMemory(tmp_path/'b.json')
    first=a.remember('For Cedar briefings use bullet points.',80,evidence='Use bullet points',source='lo')
    b.merge(a.public(False)['items'])
    user='Correction: for Cedar briefings use a short paragraph, not bullet points.'
    def model(messages):
        assert first['id'] in messages[1]['content']
        return json.dumps({'text':'For Cedar briefings use a short paragraph.', 'evidence':user,'target_id':first['id']})
    new,old=learning.reconcile(model,b,user,'Cedar briefings use a paragraph',90,'albert')
    assert new['id']==old['id'] and new['revision']==2
    a.merge(b.public(False)['items'])
    # Stale peer cannot revive the superseded value.
    a.merge([first])
    restarted=FabricMemory(a.path)
    assert len(restarted.load()['items'])==1
    context=learning.preference_context(restarted,'Compose our update')
    assert 'short paragraph' in context and 'bullet points' not in context
    request={'role':'user','content':'Save our update to Notes'}
    envelope=tool_workflow.envelope([{'role':'system','content':context},request],request)
    assert context in [m['content'] for m in envelope]
    assert restarted.load()['items'][0]['source']=='albert'


def test_no_unfounded_or_unknown_correction(tmp_path):
    store=FabricMemory(tmp_path/'memory.json')
    for result in [{'text':'invented','evidence':'not said','target_id':None},
                   {'text':'a fact','evidence':'said','target_id':'unknown'}]:
        with pytest.raises(ValueError):learning.reconcile(lambda _:json.dumps(result),store,'said','fact',80,'signal')
    assert not store.load()['items']


def test_capture_worker_uses_shared_records_and_no_production_files(tmp_path,monkeypatch):
    store=FabricMemory(tmp_path/'shared.json')
    saved=[]
    monkeypatch.setattr(lk,'_save_memory',lambda m:saved.append(json.loads(json.dumps(m))))
    monkeypatch.setattr(lk,'_fabric_memory_store',lambda:(store,'test'))
    monkeypatch.setattr(lk,'_fabric_memory_sync',lambda:{'ok':True,'failures':0})
    monkeypatch.setattr(lk,'_learn_from_exchange',lambda *a:False)
    monkeypatch.setattr(lk,'_living_memory_maintain',lambda b,m,mem,d:(mem,False))
    user='I prefer short paragraphs for Cedar briefings.'
    def model(base,model,messages,**kw):
        if 'Extract a reusable' in messages[0]['content']:
            return json.dumps({'text':user,'evidence':user,'target_id':None})
        return '80|'+user
    monkeypatch.setattr(lk,'_local_chat_once',model)
    memory=lk._remember_exchange('','',lk._empty_memory(),user,'Acknowledged',cognition={'interface':'Signal'})
    assert memory['extraction_diagnostic']['status']=='accepted'
    assert store.load()['items'][0]['source']=='Signal'
    assert 'short paragraphs' in learning.preference_context(store,'Write an update')


def test_skill_storage_has_no_twenty_four_item_dead_end(tmp_path,monkeypatch):
    path=tmp_path/'skills.md'
    path.write_text('## Learned\n'+''.join(f'- Useful practice number {i}.\n' for i in range(24)))
    monkeypatch.setattr(lk,'SKILLS_FILE',path)
    monkeypatch.setattr(lk,'_ensure_intelligence_files',lambda:None)
    monkeypatch.setattr(lk,'_update_skill_meta',lambda *a:None)
    monkeypatch.setattr(lk,'_load_skill_state',lambda:{'skills':{}})
    assert lk._append_learned_skill('Verify actual outcomes before reporting completion')
    assert len(lk._learned_skills())==25
    assert lk._effective_skills_text().count('\n- ')==24


def test_final_response_is_the_saved_exchange():
    # The production turn has one persistence tail; guards may replace message before this.
    source=(ROOT/'look/lk').read_text()
    tail=source[source.index('            feedback_queued=_queue_skill_feedback'):source.index('\ndef _c(text, code):')]
    assert '_save_recent_exchange(prompt, final)' in tail
    assert '_queue_memory_exchange(base, model, prompt, final,' in tail


def test_punctuation_is_not_a_filesystem_request():
    assert not lk._lo_requires_filesystem_action('I prefer concise briefings. Please remember this.')
    assert not lk._lo_requires_filesystem_action('Write a two-sentence status briefing. Use my preferred opening.')
    assert lk._lo_requires_filesystem_action('Please write a file named brief.md')
    assert lk._lo_requires_filesystem_action('Create ./brief.md')


def test_correction_replaces_candidate_even_when_extractor_uses_reinforcement(tmp_path,monkeypatch):
    store=FabricMemory(tmp_path/'shared.json')
    old=store.remember('User prefers Captain AMBER as form of address.',80,evidence='Captain AMBER',source='lo')
    memory=lk._empty_memory()
    memory=lk._add_memory(memory,old['text'],80)
    user='Correction: user prefers Captain COBALT as form of address, not Captain AMBER.'
    monkeypatch.setattr(lk,'_save_memory',lambda m:None)
    monkeypatch.setattr(lk,'_fabric_memory_store',lambda:(store,'test'))
    monkeypatch.setattr(lk,'_fabric_memory_sync',lambda:{'ok':True})
    monkeypatch.setattr(lk,'_learn_from_exchange',lambda *a:False)
    monkeypatch.setattr(lk,'_living_memory_maintain',lambda b,m,mem,d:(mem,False))
    monkeypatch.setattr(lk,'_high_recall_memory_candidate',lambda u:None)
    monkeypatch.setattr(lk,'_obvious_memory_candidate',lambda u:None)
    monkeypatch.setattr(lk,'_explicit_memory_hint',lambda u:None)
    def model(base,model,messages,**kw):
        if 'Extract a reusable' in messages[0]['content']:
            return json.dumps({'text':'User prefers Captain COBALT as form of address.','evidence':user,'target_id':old['id']})
        return 'NONE'
    monkeypatch.setattr(lk,'_local_chat_once',model)
    result=lk._remember_exchange('','',memory,user,'Acknowledged')
    assert all('AMBER' not in row['text'] for row in result['memories'])
    assert 'COBALT' in store.load()['items'][0]['text']


def test_old_local_memory_migration_does_not_resurrect_corrected_record(tmp_path,monkeypatch):
    store=FabricMemory(tmp_path/'shared.json')
    old=store.remember('Old preference',80,evidence='Old preference',source='lo')
    store.remember('New preference',80,evidence='New preference',source='signal',target_id=old['id'])
    monkeypatch.setattr(lk,'_fabric_memory_store',lambda:(store,'test'))
    memory={'durable':[{'text':'Old preference','importance':80}]}
    lk._publish_durable_memory(memory)
    assert [r['text'] for r in store.load()['items']]==['New preference']
    assert memory['shared_migration_version']==1


def test_literal_score_placeholder_is_conservative_and_observable():
    assert learning.parse_candidate('NN|60 User prefers quiet rooms.')==((40,'User prefers quiet rooms.'),'recovered_format')


def test_repeated_worker_errors_preserve_evidence_without_queue_block(tmp_path,monkeypatch):
    path=tmp_path/'job.json';path.write_text(json.dumps({'user':'synthetic evidence'}))
    monkeypatch.setattr(lk,'_load_memory',lambda:{})
    monkeypatch.setattr(lk,'_save_memory',lambda m:None)
    for _ in range(lk.MEMORY_JOB_MAX_ATTEMPTS):lk._record_memory_job_error(path,TimeoutError())
    assert not path.exists()
    assert json.loads(path.with_suffix('.failed').read_text())['user']=='synthetic evidence'


def test_forgetting_replicates_without_stale_resurrection(tmp_path):
    a=FabricMemory(tmp_path/'a.json');b=FabricMemory(tmp_path/'b.json')
    a.remember('A private preference',80,evidence='private preference',source='lo')
    stale=a.public(False)['items']
    b.merge(stale)
    assert a.forget('private')==1
    b.merge(a.public(False)['items']);b.merge(stale)
    assert b.relevant(query='private')==[]
    assert 'private preference' not in b.path.read_text()


def test_conversation_first_pass_is_bounded_and_can_request_tools():
    u={'role':'user','content':'What is my preferred form of address?'}
    result=learning.conversation_envelope([
        {'role':'system','content':'Huge unrelated capability manual'},
        {'role':'assistant','content':'Prior conversational answer'},u],u,'USER MEMORY CONTEXT: Captain COBALT')
    assert 'Huge unrelated' not in str(result)
    assert 'NEED_TOOLS' in result[0]['content']
    assert 'Captain COBALT' in str(result)
    assert result[-1] is u


def test_peer_forget_clears_stale_local_summary(tmp_path,monkeypatch):
    store=FabricMemory(tmp_path/'shared.json')
    old=store.remember('Old preference',80,evidence='Old preference',source='lo')
    store.remember('New preference',80,evidence='New preference',source='signal',target_id=old['id'])
    store.forget('New preference')
    monkeypatch.setattr(lk,'_fabric_memory_store',lambda:(store,'test'))
    memory={'durable':[{'text':'Old preference'}], 'memories':[{'text':'New preference'}], 'core_summary':'Old preference'}
    updated=lk._apply_shared_corrections(memory)
    assert not updated['durable'] and not updated['memories'] and not updated['core_summary']


def test_concurrent_correction_requires_fresh_evidence_snapshot(tmp_path):
    store=FabricMemory(tmp_path/'memory.json')
    first=store.remember('Old',80,evidence='Old',source='lo')
    store.remember('New',80,evidence='New',source='signal',target_id=first['id'])
    with pytest.raises(ValueError,match='changed during reconciliation'):
        store.remember('Stale result',80,evidence='Stale result',source='albert',target_id=first['id'],expected_updated_at=first['updated_at'])
    assert store.load()['items'][0]['text']=='New'
