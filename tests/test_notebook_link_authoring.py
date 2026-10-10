from pathlib import Path
from unittest.mock import Mock

import pytest
from look import notebook, notebook_markdown as md, look_renderer as renderer
from look.notebook_core import Notebook
from test_notebook_interaction import terminal


@pytest.mark.parametrize('label,target',[
    ('Project [draft] *ready*','/Users/me/Project Files/a(b).py'),
    ('界 👩\u200d💻 \\ backup','@3090:/home/me/a directory'),
    ('Website','https://example.com/search?q=test'),
    ('Another note','note:'+'a'*32)])
def test_generated_links_render_labels_literally_and_preserve_target(label,target):
    source=notebook.make_link(label,target)
    assert md.extract_links(source)==[(label,target)]
    assert notebook.link_fields(source)==(target,label)


def test_copy_link_from_filtered_list_keeps_focus_and_uses_full_id(tmp_path,terminal,monkeypatch,capsys):
    store=Notebook(tmp_path);identity=store.create('Alpha [project]')['note'];store.create('Beta')
    copied=Mock(return_value=True);monkeypatch.setattr(renderer,'copy_text',copied)
    keys=iter(['a','l','Y','esc','q'])
    notebook.workspace(store,None,lambda *args:next(keys),lambda text,width:text[:width])
    assert md.extract_links(copied.call_args.args[0])==[('Alpha [project]','note:'+identity)]
    assert capsys.readouterr().out.count('FILTER al█')>=2


def test_preview_copy_is_read_only(tmp_path,terminal,monkeypatch,capsys):
    store=Notebook(tmp_path);store.create('Project');row=store.list()[0]
    copied=Mock(return_value=True);monkeypatch.setattr(renderer,'copy_text',copied)
    keys=iter(['Y','esc'])
    notebook.note_view(store,row,lambda *args:next(keys))
    assert copied.call_args.args[0]==notebook.make_link('Project','note:'+row['id'])
    assert store.list()[0]['revision']==row['revision']
    assert 'Copied note link' in capsys.readouterr().out


def test_clipboard_path_can_be_named_and_inserted_at_cursor(terminal,monkeypatch):
    monkeypatch.setattr(renderer,'clipboard_text',lambda:'/Users/me/Project Files')
    keys=iter(['shiftleft','\x0b','paste:Mac project','\r','\x13'])
    result=notebook.capture_note(5,lambda *args:next(keys),' existing')
    assert result=='[Mac project](</Users/me/Project Files>) existing'


def test_copied_note_markdown_can_be_pasted_directly_or_renamed(terminal,monkeypatch):
    copied=notebook.make_link('Original [title]','note:'+'a'*32)
    monkeypatch.setattr(renderer,'clipboard_text',lambda:copied)
    keys=iter(['\x0b','\r','\x13'])
    assert notebook.capture_note(5,lambda *args:next(keys))==copied
    keys=iter(['paste:'+copied,'\x13'])
    assert notebook.capture_note(5,lambda *args:next(keys))==copied


def test_picker_finds_named_note_among_one_hundred_without_exposing_ids(tmp_path,terminal,monkeypatch,capsys):
    store=Notebook(tmp_path)
    for index in range(100): store.create('Note '+str(index))
    target=store.create('Build plan',project='Mercury')['note']
    monkeypatch.setattr(renderer,'clipboard_text',lambda:'')
    keys=iter(['\x0b','\x0e','paste:Mercury Build','\r','\r','\x13'])
    source=notebook.capture_note(5,lambda *args:next(keys),store=store)
    assert md.extract_links(source)==[('Build plan','note:'+target)]
    picker=capsys.readouterr().out.split('LINK TO NOTE',1)[1].split('INSERT LINK',1)[0]
    assert target not in picker


def test_note_picker_cancel_leaves_link_form_and_draft_unchanged(tmp_path,terminal,monkeypatch):
    store=Notebook(tmp_path);store.create('Project')
    monkeypatch.setattr(renderer,'clipboard_text',lambda:'')
    keys=iter(['\x0b','\x0e','esc','esc','\x13'])
    assert notebook.capture_note(5,lambda *args:next(keys),'Draft',store=store)=='Draft'


def test_manual_target_rejects_unsafe_paste_then_accepts_remote_path(terminal,monkeypatch,capsys):
    monkeypatch.setattr(renderer,'clipboard_text',lambda:'')
    keys=iter(['paste:javascript:alert(1)','\r','home']+['delete']*len('javascript:alert(1)')+
              ['paste:@3090:/home/me/Project Files','\r','paste:Remote project','\r'])
    source=notebook.insert_link(None,5,lambda *args:next(keys))
    assert md.extract_links(source)==[('Remote project','@3090:/home/me/Project Files')]
    assert 'Use a path' in capsys.readouterr().out


@pytest.mark.parametrize('target',['https:missing','note:123','@3090:relative','/path\x1b[2J','/path\u009b2J'])
def test_authoring_rejects_unsafe_or_invalid_targets(target):
    with pytest.raises(ValueError): notebook.make_link('label',target)


def test_pasted_enter_and_ctrl_s_do_not_submit_link_dialog(terminal,monkeypatch,capsys):
    monkeypatch.setattr(renderer,'clipboard_text',lambda:'')
    keys=iter(['paste:/bad\n\x13','paste:/good path','\r','\r'])
    source=notebook.insert_link(None,5,lambda *args:next(keys))
    assert md.extract_links(source)==[('good path','/good path')]
    assert 'Paste a single' in capsys.readouterr().out


def test_clipboard_read_supports_mac_wayland_and_x11(monkeypatch):
    result=Mock(stdout='α 👩\u200d💻')
    run=Mock(return_value=result);monkeypatch.setattr(renderer.subprocess,'run',run)
    for platform,available,expected in [('darwin',{'pbpaste'},['pbpaste']),
        ('linux',{'wl-paste'},['wl-paste','--no-newline']),
        ('linux',{'xclip'},['xclip','-selection','clipboard','-o'])]:
        monkeypatch.setattr(renderer.sys,'platform',platform)
        monkeypatch.setattr(renderer.shutil,'which',lambda name:name if name in available else None)
        assert renderer.clipboard_text()==result.stdout
        assert run.call_args.args[0]==expected
    monkeypatch.setattr(renderer.shutil,'which',lambda name:None)
    assert renderer.clipboard_text()==''


def test_clipboard_timeout_keeps_manual_entry_available(terminal,monkeypatch):
    monkeypatch.setattr(renderer.shutil,'which',lambda name:name)
    monkeypatch.setattr(renderer.subprocess,'run',Mock(side_effect=renderer.subprocess.TimeoutExpired('clipboard',1)))
    keys=iter(['paste:https://example.com','\r','\r'])
    assert notebook.insert_link(None,5,lambda *args:next(keys))=='[example.com](<https://example.com>)'
