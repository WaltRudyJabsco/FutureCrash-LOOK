from unittest.mock import Mock
import pytest
from look import notebook as nb, notebook_markdown as md, look_renderer as renderer
from test_notebook_interaction import terminal


def action(source):
    actions=[];md.render(source,80,actions)
    assert len(actions)==1
    return actions[0]


def test_ctrl_k_defaults_to_link_for_path_with_spaces(terminal,monkeypatch):
    monkeypatch.setattr(renderer,'clipboard_text',lambda:'/a project folder')
    keys=iter(['enter'])
    source=nb.insert_link(None,5,lambda *args:next(keys))
    assert md.extract_links(source)==[('a project folder','/a project folder')]


def test_explicit_command_mode_inserts_clipboard_block_with_label_and_directory(terminal,monkeypatch,capsys):
    body='printf "café"\nprintf "界"'
    monkeypatch.setattr(renderer,'clipboard_text',lambda:body)
    keys=iter(['\x14','\t','paste:Open book','\t','paste:~/Projects/My Book','\x13'])
    source=nb.insert_link(None,5,lambda *args:next(keys))
    label,target=action(source)
    assert (label,target['command'],target['cwd'])==('Open book',body,'~/Projects/My Book')
    assert 'INSERT COMMAND' in capsys.readouterr().out


def test_pasted_enter_and_save_are_data_and_never_execute(terminal,monkeypatch,capsys):
    monkeypatch.setattr(renderer,'clipboard_text',lambda:'')
    execute=Mock();monkeypatch.setattr(nb.subprocess,'run',execute)
    keys=iter(['\x14','paste:bad\n\x13','paste:echo one\r\necho two','shiftenter'])
    source=nb.insert_link(None,5,lambda *args:next(keys))
    assert action(source)[1]['command']=='echo one\necho two'
    execute.assert_not_called()
    assert 'controls' in capsys.readouterr().out


def test_enter_adds_command_line_and_does_not_drop_clipboard(terminal,monkeypatch):
    monkeypatch.setattr(renderer,'clipboard_text',lambda:'echo first')
    keys=iter(['\x14','enter','paste:echo next','\x13'])
    assert action(nb.insert_link(None,5,lambda *args:next(keys)))[1]['command']=='echo first\necho next'


def test_switching_type_preserves_both_drafts(terminal,monkeypatch):
    monkeypatch.setattr(renderer,'clipboard_text',lambda:'/project folder')
    keys=iter(['paste:Project','\x14','paste:echo done','\x14','enter'])
    source=nb.insert_link(None,5,lambda *args:next(keys))
    assert md.extract_links(source)==[('Project','/project folder')]


def test_block_is_inserted_on_own_lines_even_inside_existing_text(terminal,monkeypatch):
    monkeypatch.setattr(renderer,'clipboard_text',lambda:'echo hello')
    keys=iter(['left','\x0b','\x14','\x13','\x13'])
    source=nb.capture_note(5,lambda *args:next(keys),'ab')
    assert source.startswith('a\n\n') and source.endswith('\n\nb')
    assert action(source)[1]['command']=='echo hello'


def test_backticks_in_script_round_trip_without_closing_command_fence():
    body='printf "```"\nprintf "next"'
    source=nb.make_command(body,'Quoted "label"','~/My Book')
    label,target=action(source)
    assert label=='Quoted "label"' and target['command']==body and target['cwd']=='~/My Book'


def test_cancel_leaves_note_draft_intact(terminal,monkeypatch):
    monkeypatch.setattr(renderer,'clipboard_text',lambda:'echo hello')
    keys=iter(['\x0b','\x14','esc','\x13'])
    assert nb.capture_note(5,lambda *args:next(keys),'Draft')=='Draft'


def test_link_mode_does_not_guess_multiline_commands(terminal,monkeypatch,capsys):
    monkeypatch.setattr(renderer,'clipboard_text',lambda:'echo one\necho two')
    keys=iter(['paste:echo one\necho two','esc'])
    assert nb.insert_link(None,5,lambda *args:next(keys)) is None
    assert 'Paste a single' in capsys.readouterr().out


def test_command_body_can_be_edited_with_arrows(terminal,monkeypatch):
    monkeypatch.setattr(renderer,'clipboard_text',lambda:'echo one\necho two')
    keys=iter(['\x14','up','end','left','paste:X','\x13'])
    assert 'X' in action(nb.insert_link(None,5,lambda *args:next(keys)))[1]['command']
