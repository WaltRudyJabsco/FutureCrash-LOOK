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
    monkeypatch.setattr(picker.termios,'tcgetattr',lambda fd:[picker.termios.IXON | picker.termios.IXOFF,0,0,0,0,0,[]])
    restore=Mock();monkeypatch.setattr(picker.termios,'tcsetattr',restore)
    monkeypatch.setattr(picker.tty,'setcbreak',lambda fd:None)
    keys=iter(['s','h','o','t','\n','\t','esc','a','r','e','a','\n'])
    sent=Mock()
    ui=SimpleNamespace(_command_rows=lambda:[('lk shot [all|area|record] [--save FILE.png]','files','Capture')],
        _read_tty_key=lambda fd:next(keys),_write_command_request=sent,_ansi_clip=lambda s,w:s[:w],_c=lambda s,*args:s)
    assert picker.run(ui)==0
    sent.assert_called_once_with('lk shot area [--save FILE.png]')
    assert 'OPTIONS / HELP' in out.getvalue()
    assert restore.call_args_list[0].args[2][0] & (picker.termios.IXON | picker.termios.IXOFF)==0
    assert restore.call_args_list[-1].args[2][0] & picker.termios.IXON


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


def test_control_q_exits_real_terminal_driver():
    import os,pty,select,subprocess,time
    from pathlib import Path
    root=Path(__file__).resolve().parents[1]
    master,slave=pty.openpty()
    code="""import command_picker
from types import SimpleNamespace
import os
ui=SimpleNamespace(_command_rows=lambda:[('lk shot','files','Capture')],_read_tty_key=lambda fd:os.read(fd,1).decode(),_ansi_clip=lambda s,w:s,_c=lambda s,*a:s)
command_picker.run(ui)
"""
    env=dict(os.environ,PYTHONPATH=str(root/'look'))
    proc=subprocess.Popen([sys.executable,'-c',code],stdin=slave,stdout=slave,stderr=slave,env=env)
    os.close(slave)
    try:
        output=b'';deadline=time.monotonic()+5
        while b'FILTER' not in output and time.monotonic()<deadline:
            if select.select([master],[],[],.1)[0]:output+=os.read(master,65536)
        assert b'FILTER' in output
        os.write(master,b'\x11')
        assert proc.wait(timeout=3)==0
    finally:
        if proc.poll() is None:proc.kill();proc.wait()
        os.close(master)
