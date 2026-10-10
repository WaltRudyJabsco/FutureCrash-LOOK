import os
import re
from pathlib import Path
from unittest.mock import Mock

import pytest
from look import notebook, notebook_markdown as md, look_renderer as renderer, fabric_files as ff
from look.notebook_core import Notebook
from core import file_transfer
from test_notebook_interaction import lk, terminal


def test_links_share_parser_numbering_and_ignore_code():
    text='[web](https://example.com/a(b)) **[disk](</a path>)**\n'+chr(96)+'[fake](note:no)'+chr(96)+'\n'+chr(96)*3+'\n[also fake](note:no)\n'+chr(96)*3
    links=[]
    rows=md.render(text,40,links)
    assert links==[('web','https://example.com/a(b)'),('disk','/a path')]
    assert md.extract_links(text)==links
    assert 'web [1]' in re.sub(r'\033\[[0-9;]*m','', ''.join(rows)) and 'disk' in ''.join(rows)
    assert '(https://' not in ''.join(rows)


def test_note_id_survives_rename_and_reverse_lookup(tmp_path):
    store=Notebook(tmp_path); target=store.create('Target')['note']
    source=store.create('Source\n[go](note:'+target+')')['note']
    store.change(target,{'title':'Renamed'})
    row=next(row for row in store.list() if row['id']==source)
    kind,value=notebook.resolve_link(store,row,'note:'+target)
    assert kind=='note' and value['title']=='Renamed'
    assert notebook.related_notes(store,value)==[('Source','note:'+source)]
    store.change(target,{'status':'deleted'})
    with pytest.raises(ValueError,match='missing'): notebook.resolve_link(store,row,'note:'+target)


def test_literal_paths_urls_remote_and_unsupported_schemes(tmp_path):
    store=Notebook(tmp_path); store.create('Source'); row=store.list()[0]
    path=Path(row['path']).parent/'space (one).txt'; path.write_text('hello')
    assert notebook.resolve_link(store,row,path.name)==('path',path)
    kind,dest=notebook.resolve_link(store,row,'@3090:/a path/file')
    assert kind=='fabric' and str(dest)=='@3090:/a path/file'
    assert notebook.resolve_link(store,row,'https://example.com')[0]=='url'
    for bad in ('javascript:alert(1)','https:missing','note:123','@3090:relative','/bad\x1b[2J'):
        with pytest.raises(ValueError): notebook.resolve_link(store,row,bad)


def test_preview_opens_link_and_returns_to_note(tmp_path,terminal,monkeypatch):
    store=Notebook(tmp_path); store.create('Source\n[web](https://example.com)')
    keys=iter(['L','1','\r','esc']); opened=Mock()
    monkeypatch.setattr(notebook,'open_link',opened)
    notebook.note_view(store,store.list()[0],lambda *args:next(keys))
    opened.assert_called_once_with('url','https://example.com')


def test_editor_paste_keeps_unicode_and_controls_inert(terminal,capsys):
    payload='é界 👩\u200d💻\r\nnext\x1b[2J\x13'
    keys=iter(['paste:'+payload,'\r','x','\x13'])
    result=notebook.capture_note(5,lambda *args:next(keys))
    assert result=='é界 👩\u200d💻\nnext\\x1b[2J\\x13\nx'
    output=capsys.readouterr().out
    assert '\x1b[?2004h' in output and '\x1b[?2004l' in output


def test_bracketed_paste_decoder_does_not_execute_enter_or_escape():
    read_fd,write_fd=os.pipe()
    payload='α\n\x1b[2J\x13'
    try:
        os.write(write_fd,b'\x1b[200~'+payload.encode()+b'\x1b[201~\r')
        assert lk._read_tty_key(read_fd,.1)=='paste:'+payload
        assert lk._read_tty_key(read_fd,.1)=='\r'
    finally:
        os.close(read_fd); os.close(write_fd)


def test_file_browse_keeps_directory_contract_and_adds_files(tmp_path):
    (tmp_path/'folder').mkdir(); (tmp_path/'song.txt').write_text('hello')
    result=file_transfer.browse(str(tmp_path))
    assert result['directories']==[{'name':'folder','path':str(tmp_path/'folder')}]
    assert result['files']==[{'name':'song.txt','path':str(tmp_path/'song.txt')}]


def test_remote_file_link_selects_file_and_navigates_parent(terminal,monkeypatch,capsys):
    file=ff.Destination('3090','/music/song.txt'); calls=[]
    def browse(dest):
        calls.append(str(dest))
        if dest.path==file.path: raise RuntimeError('Not a directory')
        return {'path':dest.path,'directories':[],'files':[{'name':'song.txt','path':file.path}]}
    monkeypatch.setattr(ff,'browse',browse)
    keys=iter(['\r','Y','\x1b[D','\x1b'])
    monkeypatch.setattr(renderer,'read_key',lambda:next(keys))
    copied=Mock(return_value=True);monkeypatch.setattr(renderer,'copy_text',copied)
    renderer.browse_fabric(file)
    copied.assert_called_once_with(str(file))
    assert calls==[str(file),'@3090:/music','@3090:/']
    assert 'song.txt' in capsys.readouterr().out


def test_direct_number_shortcut_preserved(tmp_path,terminal,monkeypatch):
    store=Notebook(tmp_path);store.create('Source\n[web](https://example.com)')
    keys=iter(['1','esc']);opened=Mock()
    monkeypatch.setattr(notebook,'open_link',opened)
    notebook.note_view(store,store.list()[0],lambda *args:next(keys))
    opened.assert_called_once_with('url','https://example.com')


def test_related_selector_navigates_to_renamed_note(tmp_path,terminal,monkeypatch,capsys):
    store=Notebook(tmp_path);target=store.create('Target')['note']
    source=store.create('Source\n[Target](note:'+target+')')['note']
    store.change(source,{'title':'Renamed source'})
    row=next(row for row in store.list() if row['id']==target)
    keys=iter(['B','\r','esc'])
    notebook.note_view(store,row,lambda *args:next(keys))
    assert 'Renamed source' in capsys.readouterr().out


def test_failed_external_open_restores_terminal(tmp_path,terminal,monkeypatch,capsys):
    store=Notebook(tmp_path);store.create('Source\n[web](https://example.com)')
    keys=iter(['1','esc'])
    monkeypatch.setattr(notebook,'open_link',Mock(side_effect=OSError('Unavailable')))
    notebook.note_view(store,store.list()[0],lambda *args:next(keys))
    assert 'Unavailable' in capsys.readouterr().out
    notebook.termios.tcsetattr.assert_called_with(5,notebook.termios.TCSADRAIN,['old'])
