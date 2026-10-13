import json,time
from pathlib import Path
from unittest.mock import Mock
import pytest
from core import fabric_care as care


def snapshot():return {'self':{'name':'home'},'peers':[{'name':'away','trusted':True},{'name':'stranger','trusted':False}]}


def reader(target,path):
    if 'release' in path:return {'digest':'same','commit':'abc1234'}
    if 'maintenance/status' in path:return {'state':'healthy'}
    return {'owner':target,'configured':target=='local','connected':True,'receipts':[{'node':target,'restore_tested':True,'verified_at':time.time()}]}


@pytest.mark.parametrize('text,operation',[
 ('check our Fabric','status'),('are we all backed up and up to date?','status'),
 ('make sure we’re all backed up and up to date','ensure'),
 ('back up our fabric','backup'),('update all computers from 3090','sync'),
 ('can you update all computers from this computer','sync')])
def test_clear_upkeep_intents(text,operation):assert care.intent(text)['operation']==operation


@pytest.mark.parametrize('text',['how do backups work in our fabric?','do not update our computers','why are our computers slow','play the backup song','can you explain fabric updates','back up this document'])
def test_discussion_and_unrelated_phrases_do_not_mutate(text):assert care.intent(text) is None


def test_status_only_trusted_nodes_and_never_posts():
    post=Mock();report=care.operate('status','',snapshot(),reader,post)
    assert [r['node'] for r in report['nodes']]==['home','away']
    assert report['releases_match'] and all(r['backup']['verified_recently'] for r in report['nodes'])
    assert not post.called


def test_missing_offline_checks_remain_unknown():
    def read(target,path):
        if target=='away':raise TimeoutError('offline')
        return reader(target,path)
    report=care.inspect(snapshot(),read)
    assert not report['releases_match'] and len(report['nodes'][1]['errors'])==3
    assert 'offline' in care.describe(report)


def test_owner_receipts_cover_a_contributor_by_identity():
    def read(target,path):
        data=reader(target,path)
        if 'recovery' in path:
            data['receipts']=[] if target=='away' else [{'node':'away','restore_tested':True,'verified_at':time.time()}]
        return data
    report=care.inspect(snapshot(),read)
    assert report['nodes'][1]['backup']['verified_recently']


def test_old_or_unverified_receipt_is_not_protection():
    def read(target,path):
        data=reader(target,path)
        if 'recovery' in path:data['receipts']=[{'node':target,'verified_at':time.time(),'restore_tested':False},{'node':target,'verified_at':time.time()-care.BACKUP_MAX_AGE-1,'restore_tested':True}]
        return data
    assert not any(r['backup']['verified_recently'] for r in care.inspect(snapshot(),read)['nodes'])


def test_sync_requires_source_and_posts_once_to_each_different_peer():
    def read(target,path):
        data=reader(target,path)
        if 'release' in path:data['digest']=target
        return data
    post=Mock(return_value={'ok':True,'state':'staged','job':'job'})
    missing=care.operate('sync','',snapshot(),read,post)
    assert missing['next'] and not post.called
    report=care.operate('sync','local',snapshot(),read,post)
    assert post.call_args.args==('away','/v1/maintenance/update',{'source':'home','digest':'local','confirm':True})
    assert 'pending' in care.describe(report) and len(report['actions'])==1
    with pytest.raises(ValueError):care.operate('sync','stranger',snapshot(),read,post)


def test_ensure_runs_only_stale_configured_owners():
    def read(target,path):
        data=reader(target,path)
        if 'recovery' in path:data['receipts']=[]
        return data
    post=Mock(return_value={'ok':True,'state':'queued'})
    report=care.operate('ensure','',snapshot(),read,post)
    assert post.call_args.args==('home','/v1/recovery/run',{})
    assert post.call_count==1 and report['releases_match']


def test_unconfigured_backup_does_not_initialize_disk(tmp_path,monkeypatch):
    monkeypatch.setattr(care,'backup_status',lambda home:{'job':{},'configured':False,'setup':'setup'})
    spawn=Mock();monkeypatch.setattr(care.subprocess,'Popen',spawn)
    assert care.start_backup(tmp_path)['state']=='needs_setup'
    assert not spawn.called


def test_worker_does_not_call_skipped_backup_verified(tmp_path,monkeypatch):
    state=care.recovery.root(tmp_path);state.mkdir(parents=True)
    care.recovery.private_json(state/'care-job.json',{'id':'job','state':'queued'})
    monkeypatch.setattr(care.recovery,'backup',lambda home:{'skipped':'backup already running'})
    care.worker(tmp_path,'job')
    result=json.loads((state/'care-job.json').read_text())
    assert result['state']=='incomplete' and not result['verified']


def test_job_success_requires_restore_test(tmp_path,monkeypatch):
    state=care.recovery.root(tmp_path);state.mkdir(parents=True)
    care.recovery.private_json(state/'care-job.json',{'id':'job','state':'queued'})
    monkeypatch.setattr(care.recovery,'backup',lambda home:{'restore_tested':True})
    care.worker(tmp_path,'job')
    assert json.loads((state/'care-job.json').read_text())['state']=='complete'


def test_remote_care_gateway_is_not_peer_control(monkeypatch):
    from types import SimpleNamespace
    from core import node
    handler=object.__new__(node.API);handler.server=SimpleNamespace(plane='ingress');handler.headers={}
    monkeypatch.setattr(handler,'sendj',lambda code,data:(code,data))
    code,data=handler._care({'operation':'sync','source':'local'})
    assert code==403 and 'local-control' in data['error']


def test_albert_and_signal_share_the_care_engine_entry():
    from look import lo_engine
    from core import cognition
    rows=cognition.public_registry()
    assert any(r['id']=='fabric.status' for r in rows)
    assert any(r['id']=='fabric.maintain' for r in rows)
    source=(Path(__file__).resolve().parents[1]/'albert/server.py').read_text()
    signal=(Path(__file__).resolve().parents[1]/'signal-window/server.py').read_text()
    assert 'profile="workspace"' in source and 'engine.chat_once(' in source
    assert 'lo_engine.chat_once(' in signal or '_load_lo_engine' in signal or 'engine.chat_once(' in signal


def test_invalid_source_is_rejected_without_actions():
    post=Mock()
    with pytest.raises(ValueError):care.operate('sync',['bad'],snapshot(),reader,post)
    with pytest.raises(ValueError):care.operate('sync','$(shell)',snapshot(),reader,post)
    assert not post.called


def test_fresh_owner_runs_plan_when_contributor_is_stale():
    def read(target,path):
        data=reader(target,path)
        if 'recovery' in path and target=='away':data['receipts']=[]
        return data
    post=Mock(return_value={'ok':True,'state':'queued'})
    care.operate('ensure','',snapshot(),read,post)
    assert post.call_args.args==('home','/v1/recovery/run',{})


def test_explicit_backup_runs_even_with_fresh_receipts():
    post=Mock(return_value={'ok':True,'state':'queued'})
    care.operate('backup','',snapshot(),reader,post)
    assert post.call_count==1
