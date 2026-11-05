import json
from pathlib import Path
from unittest.mock import Mock

import pytest
from look import notebook
from look.notebook_core import Notebook, HOME_NOTE_ID


def test_home_created_once_survives_rename_and_never_overwrites(tmp_path,monkeypatch):
    store=Notebook(tmp_path);sync=Mock();monkeypatch.setattr(notebook,'nudge_sync',sync)
    assert notebook.home_state(store)['state']=='missing'
    assert not store.list()
    first=notebook.home_state(store,True)['note']
    assert first['id']==HOME_NOTE_ID
    store.change(first['id'],{'title':'My front door','body':'Custom projects'})
    second=notebook.home_state(store,True)['note']
    assert second['title']=='My front door' and second['body']=='Custom projects'
    assert len(store.list())==1 and sync.call_count==1
    store.change(first['id'],{'status':'deleted'})
    assert notebook.home_state(store,True)['state']=='missing'
    assert not store.list()


def test_home_preserves_unrelated_home_and_offline_conflicts(tmp_path,monkeypatch):
    monkeypatch.setattr(notebook,'nudge_sync',lambda:None)
    a=Notebook(tmp_path/'a',origin='one');b=Notebook(tmp_path/'b',origin='two')
    ordinary=a.create('Home\nExisting personal note')['note']
    notebook.home_state(a,True);notebook.home_state(b,True)
    assert ordinary!=HOME_NOTE_ID
    a.exchange(b.snapshot(),[])
    state=notebook.home_state(a,True)
    assert state['state']=='needs_choice' and len(state['choices'])==2
    assert all(row['id'] for row in state['choices'])
    assert any(row['id']==ordinary for row in a.list())


def test_home_cli_and_read_only_tools(tmp_path,monkeypatch,capsys):
    store=Notebook(tmp_path);monkeypatch.setattr(notebook,'Notebook',lambda:store)
    monkeypatch.setattr(notebook,'nudge_sync',lambda:None)
    assert json.loads(notebook.tool('notebook_home',{}))['state']=='missing'
    assert notebook.main(['home','--json'])==0
    state=json.loads(capsys.readouterr().out)
    assert state['note']['id']==HOME_NOTE_ID
    assert notebook.main(['home','--json'])==0
    assert len(store.list())==1
    links=json.loads(notebook.tool('notebook_links',{'id':HOME_NOTE_ID}))
    assert len(links['links'])==6
    assert all(row['kind']=='action' and not row['executed'] for row in links['links'])
    assert 'radio_add' in next(row for row in notebook.action_catalog() if row['id']=='ytr')['tools']


def test_fixed_action_links_cannot_smuggle_shell_arguments(tmp_path,monkeypatch):
    store=Notebook(tmp_path);store.create('Source');row=store.list()[0]
    run=Mock();monkeypatch.setattr(notebook.subprocess,'run',run)
    for action in notebook.action_catalog():
        link=notebook.make_link(action['label'],action['link'])
        assert action['link'] in link
        kind,target=notebook.resolve_link(store,row,action['link'])
        notebook.open_link(kind,target)
        assert run.call_args.args[0][-1]==notebook.FABRIC_ACTIONS[action['id']][1][-1]
        assert run.call_args.kwargs.get('shell') is None
    for bad in ('look:museum;rm -rf /','look:ytr https://example.com','look:unknown','look:../museum','look:museum?arg=x'):
        with pytest.raises(ValueError):notebook.link_target(bad)
        with pytest.raises(ValueError):notebook.resolve_link(store,row,bad)


def test_link_inspection_keeps_command_and_terminal_numbering_without_running(tmp_path,monkeypatch):
    store=Notebook(tmp_path)
    store.create('Test\n[Museum](look:museum)\n'+notebook.make_command('echo hello','Greeting')+'\n'+notebook.make_command('','Shell',kind='terminal'))
    run=Mock(side_effect=AssertionError('inspection executed a command'))
    monkeypatch.setattr(notebook.subprocess,'run',run)
    result=notebook.inspect_note_links(store,store.list()[0])
    assert [row['kind'] for row in result['links']]==['action','command','terminal']
    assert [row['number'] for row in result['links']]==[1,2,3]
    assert all(row['requires_confirmation'] for row in result['links'][1:])
    run.assert_not_called()


def test_home_alias_and_ai_registration():
    root=Path(__file__).resolve().parents[1]
    assert 'lknh() { command lk notes home "$@"; }' in (root/'look/zshrc').read_text()
    names={tool['function']['name'] for tool in notebook.tools()}
    assert {'notebook_home','notebook_actions','notebook_links'}<=names
    from core import cognition
    for name in ('notebook_home','notebook_actions','notebook_links'):
        assert name in cognition.FAMILY_TOOLS['memory']
        assert '"'+name+'":("all","observation")' in (root/'look/lk').read_text()


def test_fabric_picker_inserts_portable_link(monkeypatch):
    from look import look_renderer
    monkeypatch.setattr(look_renderer,'clipboard_text',lambda:'')
    keys=iter(['\x01','2','\r','\r'])
    result=notebook.insert_link(None,5,lambda *args:next(keys))
    assert notebook.link_fields(result)==('look:museum','Museum')
    assert notebook.link_fields('look:museum')==('look:museum','Museum')


def test_home_tools_survive_conservative_ai_routing(monkeypatch):
    from test_notebook_interaction import lk
    from core import cognition
    monkeypatch.setattr(lk,'_cognition_module',lambda:cognition)
    route=lk._lo_cognition_route('show my fabric home note',use_openjev=False)
    names={tool['function']['name'] for tool in lk._lo_tools_for_route('conservative',route)}
    assert {'notebook_home','notebook_actions','notebook_links'}<=names


from test_notebook_interaction import terminal

@pytest.mark.parametrize('activate',[False,True])
def test_home_note_numbered_link_requires_activation_and_returns(tmp_path,terminal,monkeypatch,activate):
    store=Notebook(tmp_path);monkeypatch.setattr(notebook,'nudge_sync',lambda:None)
    row=notebook.home_state(store,True)['note']
    launch=Mock();monkeypatch.setattr(notebook,'open_link',launch)
    keys=iter(['1','esc'] if activate else ['esc'])
    notebook.note_view(store,row,lambda *args:next(keys))
    if activate:launch.assert_called_once_with('action','museum')
    else:launch.assert_not_called()
    assert notebook.home_state(store)['note']['revision']==row['revision']
