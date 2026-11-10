import io
import sys
from types import SimpleNamespace
from unittest.mock import Mock
import command_picker as picker


def test_catalog_excludes_shortcuts_and_expands_safe_alternatives():
    rows=[('l [PATH]','files','Files'),('lk shot [all|area|record] [--save FILE.png]','files','Capture'),('lk _worker','internal','Worker')]
    catalog=picker.groups(rows)
    assert list(catalog)==['shot']
    assert ('lk shot area [--save FILE.png]','files','Capture') in picker.forms(catalog['shot'])


def test_browse_search_help_back_and_edit_without_execution(monkeypatch):
    out=io.StringIO();out.isatty=lambda:True
    monkeypatch.setattr(sys,'stdout',out)
    monkeypatch.setattr(sys,'stdin',SimpleNamespace(isatty=lambda:True,fileno=lambda:0))
    monkeypatch.setattr(picker.termios,'tcgetattr',lambda fd:[])
    restore=Mock();monkeypatch.setattr(picker.termios,'tcsetattr',restore)
    monkeypatch.setattr(picker.tty,'setcbreak',lambda fd:None)
    keys=iter(['s','h','o','t','\n','\t','esc','a','r','e','a','\n'])
    sent=Mock()
    ui=SimpleNamespace(_command_rows=lambda:[('lk shot [all|area|record] [--save FILE.png]','files','Capture')],
        _read_tty_key=lambda fd:next(keys),_write_command_request=sent,_ansi_clip=lambda s,w:s[:w],_c=lambda s,*args:s)
    assert picker.run(ui)==0
    sent.assert_called_once_with('lk shot area [--save FILE.png]')
    assert 'OPTIONS / HELP' in out.getvalue()
    restore.assert_called_once()


def test_noninteractive_lists_forms(monkeypatch,capsys):
    monkeypatch.setattr(sys,'stdin',SimpleNamespace(isatty=lambda:False))
    ui=SimpleNamespace(_command_rows=lambda:[('lk shot [all|area]','files','Capture')])
    assert picker.run(ui)==0
    assert 'lk shot area' in capsys.readouterr().out


def test_file_shortcut_implementation_unchanged():
    from pathlib import Path
    import subprocess
    root=Path(__file__).resolve().parents[1]
    current=(root/'look/zshrc').read_text()
    previous=subprocess.check_output(['git','show','main:look/zshrc'],cwd=root,text=True)
    start='# Human-facing smart-view implementation.'
    end='# ── Personal tools / projects'
    assert current.split(start)[1].split(end)[0]==previous.split(start)[1].split(end)[0]
