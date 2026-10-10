import io
import json
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import Mock
from types import SimpleNamespace

import pytest
from look import terminal_style as styles

ROOT=Path(__file__).resolve().parents[1]


def folder(tmp_path,monkeypatch):
    path=tmp_path/'kitty';path.mkdir()
    (path/'kitty.conf').write_text((ROOT/'terminal/kitty.conf').read_text())
    monkeypatch.setenv('KITTY_CONFIG_DIRECTORY',str(path))
    monkeypatch.delenv('LOOK_TERMINAL_THEME',raising=False)
    return path


def test_paper_explicit_rgb_directory_and_markdown_file_are_dark(tmp_path,monkeypatch):
    path=folder(tmp_path,monkeypatch);styles.select_theme('paper',path)
    data=styles.application_colors()
    assert data['WHITE']==(32,30,26)
    for key,value in data.items():
        if not key.startswith('ACTIVE_'):
            color='#'+''.join(format(channel,'02x') for channel in value)
            assert styles.contrast('#f6f1e7',color)>=4.5
    code=r'''
from pathlib import Path
from look import look_renderer as renderer
path=Path(__import__('sys').argv[1])
path.mkdir(); (path/'notes.md').write_text('Notes')
lines=renderer.build_view(path,'smart',False,100,2)
assert renderer.WHITE=='\x1b[38;2;32;30;26m',renderer.WHITE
output='\n'.join(lines)
assert renderer.WHITE+str(path) in output,output
assert renderer.WHITE in renderer.color_for(renderer.read_entries(path,False)[0])
assert '\x1b[38;2;224;229;236m' not in output
print('Real LOOK directory heading and Markdown label use dark ink')
'''
    env=dict(os.environ,COLORTERM='truecolor')
    subprocess.run([sys.executable,'-c',code,str(tmp_path/'listing')],cwd=ROOT,env=env,check=True)


def test_neon_slate_and_reset_keep_existing_renderer_colors(tmp_path,monkeypatch):
    path=folder(tmp_path,monkeypatch)
    for name in ('neon','slate','reset'):
        styles.select_theme(name,path)
        assert styles.application_colors()=={}


def test_launched_palette_overrides_saved_palette_for_app_colors(tmp_path,monkeypatch):
    path=folder(tmp_path,monkeypatch);styles.select_theme('slate',path)
    monkeypatch.setenv('LOOK_TERMINAL_THEME','paper')
    assert styles.application_colors()['WHITE']==(32,30,26)


def test_custom_roles_update_app_and_terminal_accents_and_tab_contrast(tmp_path,monkeypatch):
    path=folder(tmp_path,monkeypatch)
    values=dict(styles.CUSTOM_DEFAULTS,accent='#213f65',tabs='#a65c1a')
    (path/'look-custom.json').write_text(json.dumps(values))
    styles.select_theme('custom',path)
    palette=styles.settings('custom',path)
    assert styles.application_colors()['CYAN']==(33,63,101)
    assert palette['color252']==values['foreground']
    assert palette['active_tab_background']=='#a65c1a'
    assert styles.contrast(palette['active_tab_background'],palette['active_tab_foreground'])>=4.5


@pytest.fixture
def terminal(monkeypatch):
    class Output(io.StringIO):
        def isatty(self): return True
    output=Output()
    monkeypatch.setattr(styles,'sys',SimpleNamespace(stdin=Mock(isatty=lambda:True,fileno=lambda:5),
        stdout=output,stderr=sys.stderr))
    monkeypatch.setattr(styles.termios,'tcgetattr',lambda fd:['old'])
    monkeypatch.setattr(styles.termios,'tcsetattr',Mock())
    monkeypatch.setattr(styles.tty,'setcbreak',Mock())
    return output


def test_selector_changes_one_custom_style_and_saves_after_explicit_s(tmp_path,monkeypatch,terminal):
    path=folder(tmp_path,monkeypatch);monkeypatch.setattr(styles,'reload_kitty',lambda:False)
    # Background Mercury→Albert; commit selection, then save.
    keys=iter(['\r','down','\r','S'])
    assert styles.customize(lambda *args:next(keys),path)
    assert json.loads((path/'look-custom.json').read_text())['background']=='#f3efe3'
    assert (path/'look-theme.conf').read_text().startswith('# LOOK palette: custom')
    styles.termios.tcsetattr.assert_called_with(5,styles.termios.TCSADRAIN,['old'])


def test_cancel_keeps_active_style_and_custom_file_unchanged(tmp_path,monkeypatch,terminal):
    path=folder(tmp_path,monkeypatch);styles.select_theme('slate',path)
    original=(path/'look-theme.conf').read_bytes()
    keys=iter(['\r','down','\r','esc'])
    assert not styles.customize(lambda *args:next(keys),path)
    assert (path/'look-theme.conf').read_bytes()==original
    assert not (path/'look-custom.json').exists()


def test_selector_rejects_faint_ink_before_saving(tmp_path,monkeypatch,terminal):
    path=folder(tmp_path,monkeypatch)
    (path/'look-custom.json').write_text(json.dumps(dict(styles.CUSTOM_DEFAULTS,foreground='#fafafa')))
    keys=iter(['S','esc'])
    assert not styles.customize(lambda *args:next(keys),path)
    assert 'Increase contrast' in terminal.getvalue()
    assert not (path/'look-theme.conf').exists()


def test_invalid_custom_color_never_reaches_config(tmp_path,monkeypatch):
    path=folder(tmp_path,monkeypatch)
    (path/'look-custom.json').write_text(json.dumps({'accent':'#123\nmap x quit'}))
    with pytest.raises(ValueError):styles.select_theme('custom',path)
    assert not (path/'look-theme.conf').exists()


def test_paper_prompt_panels_contrast_with_existing_dark_os_time_and_git_text():
    palette=styles.settings('paper')
    # P10K's existing OS/time use panel 7, Git uses panels 2/3 and foreground 0.
    for foreground,background in (('#080808','color7'),(palette['color0'],'color7'),
                                 (palette['color0'],'color2'),(palette['color0'],'color3')):
        assert styles.contrast(foreground,palette[background])>=4.5
    assert styles.contrast(palette['selection_background'],palette['selection_foreground'])>=4.5
    assert palette['selection_background']=='#f3d76a'


def test_picker_edits_highlighted_preset_and_cancels_without_saving(terminal):
    keys=iter(['down','E'])
    assert styles.choose_theme(lambda *args:next(keys))==('paper',True)
    assert styles.choose_theme(lambda *args:'esc') is None


def test_fine_tuning_paper_seeds_custom_without_overwriting_preset(tmp_path,monkeypatch,terminal):
    path=folder(tmp_path,monkeypatch);monkeypatch.setattr(styles,'reload_kitty',lambda:False)
    (path/'look-custom.json').write_text(json.dumps(dict(styles.CUSTOM_DEFAULTS,accent='#213f65')))
    original=dict(styles.settings('paper'))
    assert styles.customize(lambda *args:'s',path,base='paper')
    saved=json.loads((path/'look-custom.json').read_text())
    assert saved['accent']==original['url_color']
    assert saved['selection']=='#f3d76a'
    assert styles.settings('paper')==original
    custom=styles.settings('custom',path)
    assert custom['color2']==original['color2']
    assert custom['color7']==original['color7']
    assert 'Red pen' in terminal.getvalue() and 'Selected notes.md' in terminal.getvalue()


@pytest.mark.parametrize('truecolor',[True,False])
def test_marked_filter_selection_keeps_highlighter_and_legible_text(tmp_path,monkeypatch,truecolor):
    path=folder(tmp_path,monkeypatch);styles.select_theme('paper',path)
    listing=tmp_path/'listing';listing.mkdir();(listing/'notes.md').write_text('Notes')
    code=r'''
from pathlib import Path
from look import look_renderer as r
import sys
root=Path(sys.argv[1]);note=root/'notes.md'
expected='\x1b[48;2;243;215;106m\x1b[38;2;32;30;26m'
assert r.ACTIVE.startswith(expected),repr(r.ACTIVE)
rows=r._CatalogView([note],[],root,100,note,{note.resolve()})
row=rows[0]
assert row.startswith(expected),repr(row)
assert '✓' in row and 'notes.md' in row
assert row.count(r.RESET)==1,repr(row)
entries=r.read_entries(root,False)
for row in r.column_grid(entries,100,note,{note.resolve()})+r.detail_rows(entries,100,note,{note.resolve()}):
 assert row.startswith(expected),repr(row)
 assert r.RESET not in row.split('notes.md')[0],repr(row)
'''
    env=dict(os.environ,COLORTERM='truecolor' if truecolor else '')
    subprocess.run([sys.executable,'-c',code,str(listing)],cwd=ROOT,env=env,check=True)
