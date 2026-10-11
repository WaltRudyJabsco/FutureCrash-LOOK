import re
from pathlib import Path
from unittest.mock import Mock

import pytest
from look import notebook as nb, notebook_markdown as md
from look.notebook_core import Notebook
from test_notebook_interaction import terminal


def block(command='lk help all',header='command'):
    return '```'+header+'\n'+command+'\n```'


def test_commands_and_links_share_order_without_preview_execution(monkeypatch):
    execute=Mock();monkeypatch.setattr(nb.subprocess,'run',execute)
    source='[files](</project>)\n'+block()+'\n[web](https://example.com)'
    actions=[];rows=md.render(source,40,actions)
    assert [target if isinstance(target,str) else target['kind'] for _,target in actions]==['/project','command','https://example.com']
    text=re.sub(r'\033\[[0-9;]*m','','\n'.join(rows))
    assert 'Run: lk help all [2]' in text and 'web [3]' in text
    assert md.extract_links(source)==[('files','/project'),('web','https://example.com')]
    execute.assert_not_called()


@pytest.mark.parametrize('source',[block(header='sh'),block(header='python'),block()[:-3],block(header='command nope=yes'),block(''),block(header='command label="broken')])
def test_ordinary_unclosed_and_invalid_fences_are_not_actions(source):
    actions=[];md.render(source,80,actions)
    assert not actions


def test_raw_unicode_multiline_tabs_and_quoted_directory_survive(tmp_path):
    directory=tmp_path/'My Book';directory.mkdir()
    source=block('printf "café"\n\tprintf "界"',f'command label="Open my manuscript" cwd="{directory}"')
    actions=[];md.render(source,40,actions)
    label,target=actions[0]
    assert label=='Open my manuscript' and target['command']=='printf "café"\n\tprintf "界"'
    assert nb.resolve_link(None,{'path':str(tmp_path/'note.md')},target)==('command',{'command':target['command'],'cwd':directory})


@pytest.mark.parametrize('bad',['echo \x1b[2J','echo \x00','echo \u202ehidden'])
def test_hidden_controls_cannot_be_launched(tmp_path,bad):
    actions=[];md.render(block(bad),80,actions)
    with pytest.raises(ValueError,match='controls'):nb.resolve_link(None,{'path':str(tmp_path/'note.md')},actions[0][1])


def test_working_directory_defaults_and_remote_rejection(tmp_path,monkeypatch):
    note=tmp_path/'note.md';project=tmp_path/'project';project.mkdir();monkeypatch.chdir(project)
    target={'kind':'command','command':'pwd'}
    assert nb.resolve_command({'path':str(note)},target)['cwd']==project
    assert nb.resolve_command({'path':str(note)},{**target,'cwd':'project'})['cwd']==project
    for cwd in ('@node:/project',str(tmp_path/'missing'),'bad\npath'):
        with pytest.raises(ValueError):nb.resolve_command({'path':str(note)},{**target,'cwd':cwd})


def test_confirmation_requires_run_key_and_supports_cancel(tmp_path,capsys):
    target={'command':'printf café\npwd','cwd':tmp_path}
    keys=iter(['enter','esc'])
    assert not nb.confirm_command(5,lambda *args:next(keys),target)
    keys=iter(['down','R'])
    assert nb.confirm_command(5,lambda *args:next(keys),target)
    text=capsys.readouterr().out
    plain=re.sub(r'\033\[[0-9;]*m','',text)
    assert 'printf café' in plain and str(tmp_path) in ''.join(line.strip() for line in plain.splitlines())


def test_command_runs_in_directory_with_shell_syntax_and_returns_exit_status(tmp_path,monkeypatch):
    monkeypatch.setenv('SHELL','/bin/sh');monkeypatch.setattr('builtins.input',lambda prompt:'')
    result=nb.run_note_command({'command':'pwd >cwd.txt\nprintf "café" >output.txt\nexit 7','cwd':tmp_path})
    assert result==7 and (tmp_path/'output.txt').read_text()=='café'
    assert Path((tmp_path/'cwd.txt').read_text().strip()).resolve()==tmp_path.resolve()


@pytest.mark.parametrize('key,called',[('R',True),('esc',False)])
def test_view_returns_to_same_note_after_run_or_cancel(tmp_path,terminal,monkeypatch,key,called,capsys):
    store=Notebook(tmp_path);store.create('Project\n'+block())
    row=store.list()[0];keys=iter(['1',key,'esc']);execute=Mock(return_value=7)
    monkeypatch.setattr(nb,'run_note_command',execute)
    nb.note_view(store,row,lambda *args:next(keys))
    assert execute.called==called
    assert store.list()[0]['revision']==row['revision']
    assert ('Command exited 7' if called else 'Command cancelled') in capsys.readouterr().out
    nb.termios.tcsetattr.assert_called_with(5,nb.termios.TCSADRAIN,['old'])


def test_selector_accepts_command_targets_and_multi_digit_numbers():
    target={'kind':'command','command':'pwd\nls','cwd':''}
    keys=iter(['1','0','enter'])
    assert nb.choose_link(5,lambda *args:next(keys),[('command',target)]*12)==target
