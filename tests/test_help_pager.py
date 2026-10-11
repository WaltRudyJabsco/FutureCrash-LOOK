import io
import os
from unittest.mock import Mock

import pytest
from test_notebook_interaction import lk


class Terminal(io.StringIO):
    def isatty(self): return True
    def fileno(self): return 5


@pytest.mark.parametrize('key,top',[
    ('down',1),('j',1),('up',0),('pagedown',8),('shiftdown',8),
    ('right',8),(' ',8),('shiftup',0),('left',0),('b',0),
    ('shiftright',22),('end',22),('G',22),('shiftleft',0),('home',0),('g',0),
])
def test_help_navigation_and_terminal_restore(monkeypatch,key,top):
    output=Terminal(); monkeypatch.setattr(lk.sys,'stdout',output)
    monkeypatch.setattr(lk.sys,'stdin',Terminal())
    monkeypatch.setattr(lk.shutil,'get_terminal_size',lambda default:os.terminal_size((100,10)))
    monkeypatch.setattr(lk.termios,'tcgetattr',lambda fd:['old'])
    restore=Mock(); monkeypatch.setattr(lk.termios,'tcsetattr',restore)
    monkeypatch.setattr(lk.tty,'setcbreak',Mock())
    keys=iter([key,'esc']); monkeypatch.setattr(lk,'_read_tty_key',lambda fd:next(keys))
    assert lk._page_text('\n'.join(f'row {n}' for n in range(30)))==0
    frames=output.getvalue().split('\033[2J\033[H')[1:]
    assert frames[1].startswith(f'row {top}\n')
    restore.assert_called_once_with(5,lk.termios.TCSADRAIN,['old'])


@pytest.mark.parametrize('sequence,key',[
    (b'\x1b[1;2A','shiftup'),(b'\x1b[1;2B','shiftdown'),
    (b'\x1b[1;2C','shiftright'),(b'\x1b[1;2D','shiftleft'),
    (b'\x1b[116;5u','\x14'),
])
def test_shared_decoder_consumes_whole_modified_key(sequence,key):
    read,write=os.pipe()
    try:
        os.write(write,sequence+b'q')
        assert lk._read_tty_key(read)==key
        assert lk._read_tty_key(read)=='q'
    finally:
        os.close(read); os.close(write)


def test_reference_colors_forms_headings_and_keeps_descriptions(monkeypatch):
    monkeypatch.setattr(lk.sys,'stdout',Terminal())
    body='COMMAND INDEX\nlk help all\n  [meta] Full reference\n  Shift-↑ / Shift-↓    page back / forward\n'
    result=lk._help_color(body)
    assert '\033[35m\033[1mCOMMAND INDEX' in result
    assert '\033[36m\033[1mlk help all\033[0m' in result
    assert '\033[36m\033[1mShift-↑ / Shift-↓\033[0m' in result
    assert lk._strip_ansi(result)==body
    assert '\033[2m' not in result


def test_pipe_help_is_plain_and_does_not_read_keys(monkeypatch):
    output=io.StringIO(); monkeypatch.setattr(lk.sys,'stdout',output)
    monkeypatch.setattr(lk,'_read_tty_key',Mock(side_effect=AssertionError('read pipe')))
    body='COMMAND INDEX\nlk help all\n'*30
    assert lk._help_color(body)==body
    lk._page_text(body)
    assert output.getvalue()==body
