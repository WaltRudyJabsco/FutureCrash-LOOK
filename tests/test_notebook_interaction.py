import importlib.machinery
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
from unittest.mock import Mock

import pytest
from look import notebook
from look.notebook_core import Notebook

ROOT=Path(__file__).resolve().parents[1]
loader=importlib.machinery.SourceFileLoader('notebook_key_reader',str(ROOT/'look/lk'))
spec=importlib.util.spec_from_loader(loader.name,loader)
lk=importlib.util.module_from_spec(spec); loader.exec_module(lk)


@pytest.fixture
def terminal(monkeypatch):
    monkeypatch.setattr(notebook.sys,'stdin',Mock(fileno=lambda:5))
    monkeypatch.setattr(notebook.termios,'tcgetattr',lambda fd:['old'])
    monkeypatch.setattr(notebook.termios,'tcsetattr',Mock())
    monkeypatch.setattr(notebook.tty,'setraw',Mock())
    monkeypatch.setattr(notebook.tty,'setcbreak',Mock())


def test_inline_view_edits_body_and_preserves_record_fields(tmp_path,terminal,monkeypatch,capsys):
    store=Notebook(tmp_path); store.create('To Do',kind='task',project='Work',remind_at='in 10 minutes')
    original=store.list()[0]; keys=iter(['E','shiftenter','x','\r','esc'])
    monkeypatch.setattr(notebook,'nudge_sync',lambda:None)
    notebook.note_view(store,original,lambda *args:next(keys))
    row=store.list()[0]
    assert row['body']=='To Do\nx'
    for field in ('id','title','kind','project','remind_at','status'): assert row[field]==original[field]
    assert '┌' in capsys.readouterr().out
    notebook.termios.tcsetattr.assert_called_with(5,notebook.termios.TCSADRAIN,['old'])


def test_quick_edit_cancel_creates_no_revision(tmp_path,terminal,monkeypatch):
    store=Notebook(tmp_path); store.create('Scratch'); row=store.list()[0]
    monkeypatch.setattr(notebook,'capture_note',lambda *args:None)
    assert notebook.quick_edit(store,row,5,None)==''
    assert store.list()[0]['revision']==row['revision']


def test_quick_edit_preserves_draft_when_peer_changes_note(tmp_path,terminal,monkeypatch):
    store=Notebook(tmp_path); store.create('Scratch'); row=store.list()[0]
    store.change(row['id'],{'body':'Peer text'})
    monkeypatch.setattr(notebook,'capture_note',lambda *args:'My draft')
    assert 'draft preserved' in notebook.quick_edit(store,row,5,None)
    assert store.list()[0]['body']=='Peer text'
    assert next((tmp_path/'drafts').glob('*.md')).read_text()=='My draft'


def test_inline_view_full_editor_uses_same_note(tmp_path,terminal,monkeypatch):
    store=Notebook(tmp_path); store.create('Scratch'); row=store.list()[0]
    editor=Mock(); monkeypatch.setattr(notebook,'edit',editor)
    keys=iter(['V','esc'])
    notebook.note_view(store,row,lambda *args:next(keys))
    editor.assert_called_once_with(store,row)


def test_workspace_view_returns_to_filter(tmp_path,terminal,capsys):
    store=Notebook(tmp_path); store.create('Apple')
    keys=iter(['a','\r','esc','esc','q'])
    notebook.workspace(store,None,lambda *args:next(keys),lambda text,width:text[:width])
    assert capsys.readouterr().out.count('FILTER a█')>=2


def test_capture_enter_saves_shift_enter_and_ctrl_j_add_paragraphs(terminal,capsys):
    keys=iter(['a','shiftenter','shiftenter','b','\n','c','\r'])
    assert notebook.capture_note(5,lambda *args:next(keys))=='a\n\nb\nc'
    output=capsys.readouterr().out
    assert '\033[>1u' in output
    assert output.endswith('\033[<u')
    notebook.termios.tcsetattr.assert_called_with(5,notebook.termios.TCSADRAIN,['old'])


def test_capture_escape_does_not_save_a_draft(terminal,capsys):
    keys=iter(['d','r','a','f','t','esc'])
    assert notebook.capture_note(5,lambda *args:next(keys)) is None
    assert capsys.readouterr().out.endswith('\033[<u')


def test_workspace_clears_old_screen_and_saves_multiline_capture(tmp_path,monkeypatch,terminal,capsys):
    keys=iter(['N','a','shiftenter','b','\r','q'])
    monkeypatch.setattr(notebook,'nudge_sync',lambda:None)
    store=Notebook(tmp_path)
    notebook.workspace(store,None,lambda *args:next(keys),lambda text,width:text[:width])
    output=capsys.readouterr().out
    assert output.startswith('\033[2J\033[H')
    assert '\033[K\n' in output
    assert '\033[?25h' in output
    assert store.list()[0]['body']=='a\nb'


def test_notebook_help_returns_without_losing_filter_or_records(tmp_path,terminal,capsys):
    store=Notebook(tmp_path); store.create('Apple note')
    keys=iter(['a','H','esc','esc','q'])
    notebook.workspace(store,None,lambda *args:next(keys),lambda text,width:text[:width])
    output=capsys.readouterr().out
    assert 'File (P)' in output and 'Remind (R)' in output
    assert output.count('FILTER a█')>=2
    assert len(store.list())==1


def test_full_text_toggle_and_sort_keep_focused_record(tmp_path,terminal,capsys):
    store=Notebook(tmp_path); store.create('Alpha\nHidden zebra'); store.create('Beta')
    keys=iter(['z','/','F','esc','q'])
    notebook.workspace(store,None,lambda *args:next(keys),lambda text,width:text[:width])
    output=capsys.readouterr().out
    assert 'FILTER z█' in output and 'SEARCH z█' in output
    assert 'sort created' in output
    assert 'made ' in output and 'edited ' in output
    assert len(store.list())==2


@pytest.mark.parametrize('encoded,expected',[
    (b'\x1b[13;2u','shiftenter'),(b'\x1b[27;2;13~','shiftenter'),
    (b'\x1b\r','shiftenter'),(b'\r','\r'),('é'.encode(),'é')])
def test_terminal_decoder_handles_modified_enter_and_utf8(encoded,expected):
    read_fd,write_fd=os.pipe()
    try:
        os.write(write_fd,encoded)
        assert lk._read_tty_key(read_fd,.1)==expected
    finally:
        os.close(read_fd); os.close(write_fd)


@pytest.mark.parametrize('prompt,tool,position',[
    ('what does the first note say','notebook_read',1),
    ('what does the second note say?','notebook_read',2),
    ('list the notes','notebook_list',None),
    ('what do our notes say','notebook_list',None),
    ('show my notes','notebook_list',None)])
def test_user_reported_phrases_resolve_without_model_memory(prompt,tool,position):
    result=notebook.read_intent(prompt)
    assert result['tool']==tool
    assert result['args'].get('position')==position


def test_read_and_list_return_saved_bodies_in_lkn_order(tmp_path,monkeypatch):
    store=Notebook(tmp_path)
    store.create('Older note\nOlder body')
    newest=store.create('Latest note\nLatest body')
    monkeypatch.setattr(notebook,'Notebook',lambda:store)
    first=notebook.direct_read(notebook.read_intent('what does the first note say'))
    assert 'Latest body' in first and 'Older body' not in first
    listing=json.loads(notebook.tool('notebook_list',{}))
    assert listing[0]['id']==newest['note']
    assert json.loads(notebook.tool('notebook_read',{'position':2}))['body']=='Older note\nOlder body'
    assert len(json.loads(notebook.tool('notebook_search',{})))==2
    with pytest.raises(ValueError): notebook.tool('notebook_read',{'position':99})
    assert notebook.read_intent('write a poem about the first note') is None
