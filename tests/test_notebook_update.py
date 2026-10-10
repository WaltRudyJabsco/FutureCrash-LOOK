import json
import pytest
from look import notebook
from look.notebook_core import Notebook


@pytest.fixture
def store(tmp_path,monkeypatch):
    value=Notebook(tmp_path);monkeypatch.setattr(notebook,'Notebook',lambda:value)
    monkeypatch.setattr(notebook,'nudge_sync',lambda:None);return value


def update(store,changes=None,**args):
    row=store.list(include_done=True)[0]
    return notebook.tool('notebook_update',dict(id=row['id'],revision=row['revision'],changes=changes or {},**args))


def test_append_preserves_title_metadata_and_identity(store):
    store.create('To Do\n- [ ] Milk',kind='task',project='Home',remind_at='in ten minutes')
    before=store.list()[0]
    result=json.loads(update(store,append_text='- [ ] Bread'))
    after=store.list()[0]
    assert result['note']==before['id']
    assert after['body']=='To Do\n- [ ] Milk\n- [ ] Bread'
    for key in ('id','title','kind','project','remind_at','status'):assert after[key]==before[key]


def test_reschedule_clear_and_complete(store):
    store.create('Call',kind='task',remind_at='in ten minutes')
    previous=store.list()[0]['remind_at'];update(store,{'remind_at':'in twenty minutes','due':'tomorrow'})
    assert store.list()[0]['remind_at']>previous
    update(store,{'remind_at':None});assert store.list()[0]['remind_at'] is None
    update(store,{'status':'done','remind_at':'in ten minutes'})
    assert store.list()==[] and store.list(include_done=True)[0]['remind_at'] is None


def test_stale_edit_does_not_overwrite_peer(store):
    store.create('Notes');row=store.list()[0];store.change(row['id'],{'body':'Peer'})
    with pytest.raises(ValueError,match='changed'):
        notebook.tool('notebook_update',{'id':row['id'],'revision':row['revision'],'append_text':'Mine'})
    assert store.list()[0]['body']=='Peer'


def test_update_requires_read_and_rejects_conflicts_or_empty_edits(store):
    store.create('Notes')
    with pytest.raises(ValueError,match='revision'):notebook.tool('notebook_update',{'id':store.list()[0]['id'],'changes':{'body':'x'}})
    with pytest.raises(ValueError,match='No changes'):update(store)
    with pytest.raises(ValueError,match='not both'):update(store,{'body':'replace'},append_text='append')
    with pytest.raises(ValueError,match='Unknown'):update(store,{'danger':'x'})
    with pytest.raises(ValueError,match='date/time'):update(store,{'kind':'reminder'})
