import copy
import datetime as dt
from pathlib import Path

import pytest
from look.notebook_core import Notebook, timestamp, sync_batch, SYNC_BYTES


def exchange(left, right):
    left_rows=left.snapshot()
    reply=right.exchange(left_rows,[row['id'] for row in left_rows])
    left.exchange(reply['revisions'],[row['id'] for row in left_rows])


def test_offline_conflicts_preserve_both_edits_and_resolve(tmp_path):
    left=Notebook(tmp_path/'left','Mac'); right=Notebook(tmp_path/'right','3090')
    original=left.create('Original text'); exchange(left,right)
    left.change(original['note'],{'body':'Mac offline edit'})
    right.change(original['note'],{'body':'3090 offline edit'})
    exchange(left,right)
    assert {row['body'] for row in left.list()} == {'Mac offline edit','3090 offline edit'}
    assert all(row['conflict'] for row in right.list())
    with pytest.raises(ValueError,match='Conflicting'):
        left.change(original['note'],{'status':'done'})
    left.change(original['note'],{'body':'Both edits reconciled'},resolve=True)
    exchange(left,right)
    assert len(right.list())==1
    assert right.list()[0]['body']=='Both edits reconciled'


def test_deletion_does_not_resurrect_after_offline_reconnect(tmp_path):
    left=Notebook(tmp_path/'left'); right=Notebook(tmp_path/'right')
    original=left.create('Delete me'); exchange(left,right)
    left.change(original['note'],{'status':'deleted'})
    exchange(right,left); exchange(left,right)
    assert left.list()==right.list()==[]
    assert any(row['data']['status']=='deleted' for row in right.snapshot())


def test_editor_changes_import_before_sync_and_filing_preserves_id(tmp_path):
    left=Notebook(tmp_path/'left'); right=Notebook(tmp_path/'right')
    original=left.create('Quick capture'); row=left.list()[0]
    Path(row['path']).write_text('# Longer note\n\nMultiline\ntext\n')
    left.change(original['note'],{'project':'LOOK'})
    exchange(left,right)
    saved=right.list()[0]
    assert saved['id']==original['note']
    assert saved['title']=='Longer note'
    assert saved['body']=='Multiline\ntext\n'
    assert saved['project']=='LOOK'


def test_reminder_occurrence_dedup_and_shared_acknowledgment(tmp_path):
    left=Notebook(tmp_path/'left','Mac'); right=Notebook(tmp_path/'right','3090')
    original=left.create('Due reminder',remind_at=1000,kind='reminder')
    exchange(left,right)
    first=left.pending('Mac',now=1001)[0]; second=right.pending('3090',now=1001)[0]
    assert first['event_id']==second['event_id']
    left.mark_delivered(first['event_id'])
    assert Notebook(tmp_path/'left').delivered(first['event_id'])
    left.change(original['note'],{'remind_at':2000},expected=first['revision'])
    exchange(left,right)
    assert right.pending('3090',now=1001)==[]
    later=right.pending('3090',now=2001)[0]
    assert later['event_id'] != first['event_id']
    right.change(original['note'],{'status':'done','remind_at':None},expected=later['revision'])
    exchange(right,left)
    assert left.pending('Mac',now=3000)==[]


def test_targeting_and_stale_ack_are_checked(tmp_path):
    store=Notebook(tmp_path,'Mac')
    note=store.create('Targeted',remind_at=1000,target='Mac,3090')
    assert len(store.pending('Mac',now=1001))==1
    assert len(store.pending('3090',now=1001))==1
    assert store.pending('Other',now=1001)==[]
    store.change(note['note'],{'body':'Newer'})
    with pytest.raises(ValueError,match='changed'):
        store.change(note['note'],{'status':'done'},expected=note['id'])


def test_reminder_view_includes_reminders_attached_to_tasks(tmp_path):
    store=Notebook(tmp_path)
    store.create('Task with reminder',kind='task',remind_at=1000)
    store.create('Ordinary task',kind='task')
    assert [row['title'] for row in store.list(kind='reminder')]==['Task with reminder']


def test_revision_identity_collision_is_rejected_before_writes(tmp_path):
    store=Notebook(tmp_path); row=store.create('Immutable')
    changed=copy.deepcopy(row); changed['data']['body']='Tampered'
    with pytest.raises(ValueError,match='collision'):
        store.exchange([changed],[])
    assert store.list()[0]['body']=='Immutable'


def test_cross_record_ancestry_is_rejected(tmp_path):
    store=Notebook(tmp_path); first=store.create('One'); second=store.create('Two')
    changed=copy.deepcopy(second); changed['id']='a'*32; changed['parents']=[first['id']]
    with pytest.raises(ValueError,match='ancestry'):
        store.exchange([changed],[])
    assert len(store.list())==2


@pytest.mark.parametrize('value',[float('nan'),float('inf'),True])
def test_invalid_dates(value):
    with pytest.raises(ValueError): timestamp(value)


def test_named_date_and_relative_time():
    now=dt.datetime(2026,10,9,12).timestamp()
    assert timestamp('in 10 minutes',now)==now+600
    assert dt.datetime.fromtimestamp(timestamp('Saturday 9am',now))==dt.datetime(2026,10,10,9)


def test_sync_batch_stays_within_ingress_body_budget():
    import json
    rows=[{'body':'x'*256000,'id':str(i)} for i in range(128)]
    batch=sync_batch(rows)
    assert len(batch)<128
    assert sum(len(json.dumps(row).encode()) for row in batch)<=SYNC_BYTES
