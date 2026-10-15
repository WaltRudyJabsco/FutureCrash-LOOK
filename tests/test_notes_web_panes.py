from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from look import notebook, web_desk
from look.notebook_core import Notebook


@pytest.fixture
def terminal(monkeypatch,tmp_path):
    monkeypatch.chdir(tmp_path)
    import notebook as runtime_notebook
    monkeypatch.setattr(runtime_notebook,'Notebook',lambda:Notebook(tmp_path/'web-notes'))
    monkeypatch.setattr(web_desk,'folder',lambda:tmp_path/'web')
    monkeypatch.setattr(notebook.sys,'stdin',SimpleNamespace(fileno=lambda:0))
    monkeypatch.setattr(notebook.termios,'tcgetattr',lambda *args:None)
    monkeypatch.setattr(notebook.termios,'tcsetattr',lambda *args:None)
    monkeypatch.setattr(notebook.tty,'setcbreak',lambda *args:None)
    return tmp_path


def test_notebook_list_opens_sibling_without_changing_filter_or_note(terminal,monkeypatch):
    store=Notebook(terminal/'notes');store.create('A note');original=store.list()[0]
    pane=Mock(return_value='Shell opened beside LOOK')
    monkeypatch.setattr(notebook.terminal_style,'open_pane',pane)
    keys=iter(['W','esc','esc'])
    notebook.workspace(store,None,lambda *args:next(keys),lambda text,width:text,initial_query='A')
    pane.assert_called_once_with(Path.cwd())
    assert store.list()[0]['revision']==original['revision']


def test_note_preview_retains_scroll_and_redraws_after_resize(terminal,monkeypatch,capsys):
    store=Notebook(terminal/'notes');store.create('Title\n'+'body\n'*30);row=store.list()[0]
    sizes=iter([(80,24),(120,30),(120,30)])
    monkeypatch.setattr(notebook.shutil,'get_terminal_size',lambda *args:next(sizes))
    pane=Mock(return_value='Shell opened beside LOOK')
    monkeypatch.setattr(notebook.terminal_style,'open_pane',pane)
    read=Mock(side_effect=['W','','esc'])
    notebook.note_view(store,row,read)
    pane.assert_called_once_with(Path.cwd())
    assert all(call.args[1]==1 for call in read.call_args_list)
    text=capsys.readouterr().out
    assert '─'*76 in text and '─'*96 in text
    assert 'close focused pane' in text


def test_web_desk_uses_same_pane_helper_and_keeps_selection(terminal,monkeypatch,capsys):
    pane=Mock(return_value='Shell opened beside LOOK')
    monkeypatch.setattr(web_desk.terminal_style,'open_pane',pane)
    read=Mock(side_effect=['down','W','q'])
    web_desk.desk({'bookmarks':[]},{},read,True)
    pane.assert_called_once_with(Path.cwd())
    text=capsys.readouterr().out
    assert 'Project Gutenberg' in text and 'close focused pane' in text
    assert all(call.args[1]==1 for call in read.call_args_list)


def test_pane_unavailable_message_stays_in_web_desk(terminal,monkeypatch,capsys):
    pane=Mock(return_value='Split panes need Kitty or tmux')
    monkeypatch.setattr(web_desk.terminal_style,'open_pane',pane)
    keys=iter(['W','q'])
    assert web_desk.desk({'bookmarks':[]},{},lambda *args:next(keys),True)==0
    assert 'Split panes need Kitty or tmux' in capsys.readouterr().out


def test_uppercase_w_stays_text_in_note_editor(terminal,monkeypatch):
    monkeypatch.setattr(notebook.tty,'setraw',lambda *args:None)
    pane=Mock();monkeypatch.setattr(notebook.terminal_style,'open_pane',pane)
    keys=iter(['W','shiftenter'])
    assert notebook.capture_note(0,lambda *args:next(keys))=='W'
    pane.assert_not_called()
