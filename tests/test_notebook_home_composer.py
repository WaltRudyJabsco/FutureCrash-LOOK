import json
from unittest.mock import Mock
import pytest
from look import notebook,note_composer
from look.notebook_core import Notebook,HOME_NOTE_ID

@pytest.fixture
def store(tmp_path,monkeypatch):
    value=Notebook(tmp_path)
    monkeypatch.setattr(notebook,'Notebook',lambda:value)
    monkeypatch.setattr(notebook,'nudge_sync',lambda:None)
    monkeypatch.setattr(note_composer,'candidates',lambda *a:([{'label':'Museum','target':'look:museum'}],''))
    return value

def test_draft_then_existing_update_receipt(store,monkeypatch):
    before=notebook.home_state(store,True)['note']
    body=notebook.make_link('Museum','look:museum')
    monkeypatch.setattr(note_composer,'draft',Mock(return_value={'body':body}))
    draft=json.loads(notebook.tool('notebook_home_draft',{'request':'Add Museum to Home'}))
    assert not draft['saved'] and draft['state']=='draft'
    assert notebook.home_state(store)['note']['revision']==before['revision']
    receipt=json.loads(notebook.tool(draft['apply_tool'],draft['apply_args']))
    after=notebook.home_state(store)['note']
    assert receipt['note']==HOME_NOTE_ID and after['body']==before['body'].rstrip('\n')+'\n\n'+body
    assert after['title']==before['title']
    with pytest.raises(ValueError):notebook.tool(draft['apply_tool'],draft['apply_args'])

def test_peer_edit_blocks_append(store,monkeypatch):
    notebook.home_state(store,True)
    monkeypatch.setattr(note_composer,'draft',Mock(return_value={'body':'new entry'}))
    draft=notebook.draft_home_entry(store,'add entry')
    store.change(HOME_NOTE_ID,{'body':'A newer peer edit'})
    with pytest.raises(ValueError):notebook.tool('notebook_update',draft['apply_args'])
    assert notebook.home_state(store)['note']['body']=='A newer peer edit'

def test_clarification_is_read_only_and_answer_reaches_composer(store,monkeypatch):
    before=notebook.home_state(store,True)['note']
    compose=Mock(side_effect=[{'question':'Which project?'},{'body':'Chosen project'}])
    monkeypatch.setattr(note_composer,'draft',compose)
    first=notebook.draft_home_entry(store,'add my current project')
    assert first['state']=='needs_clarification' and 'apply_args' not in first
    notebook.draft_home_entry(store,'add my current project','The blue novel')
    assert 'Answer: The blue novel' in compose.call_args.args[0]
    assert notebook.home_state(store)['note']['revision']==before['revision']

def test_missing_and_deleted_home_are_not_recreated(store,monkeypatch):
    compose=Mock();monkeypatch.setattr(note_composer,'draft',compose)
    assert notebook.draft_home_entry(store,'add a link')['state']=='missing'
    notebook.home_state(store,True);store.change(HOME_NOTE_ID,{'status':'deleted'})
    assert notebook.draft_home_entry(store,'add a link')['state']=='missing'
    compose.assert_not_called()

def test_shared_assistant_registration():
    from test_notebook_interaction import lk
    from core import cognition
    assert 'notebook_home_draft' in cognition.FAMILY_TOOLS['memory']
    assert 'notebook_home_draft' in {t['function']['name'] for t in notebook.tools()}
    assert lk._TOOL_POLICY['notebook_home_draft']==('all','observation')


def test_memory_route_keeps_draft_and_save_together(monkeypatch):
    from test_notebook_interaction import lk
    from core import cognition
    monkeypatch.setattr(lk,'_cognition_module',lambda:cognition)
    route=lk._lo_cognition_route('Add a museum link to my Home note',use_openjev=False)
    names={t['function']['name'] for t in lk._lo_tools_for_route('workspace',route)}
    assert {'notebook_home_draft','notebook_update','notebook_home'} <= names
