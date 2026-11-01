import ast
import io
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

ROOT=Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('keys,expected',[
    (['end','\n'],29),(['shiftright','\n'],29),
    (['end','home','\n'],0),(['end','shiftleft','\n'],0),
    (['pagedown','pageup','\n'],0),(['shiftdown','shiftup','\n'],0),
])
def test_commands_navigation_and_contrasting_wrapped_footer(keys,expected,monkeypatch):
    import clipboard_shelf,terminal_style
    source=ast.parse((ROOT/'look/lk').read_text())
    function=next(node for node in source.body if isinstance(node,ast.FunctionDef) and node.name=='commands_screen')
    output=io.StringIO();output.isatty=lambda:True
    monkeypatch.setattr(sys,'stdout',output)
    monkeypatch.setattr(sys,'stdin',SimpleNamespace(isatty=lambda:True,fileno=lambda:0))
    monkeypatch.setattr(terminal_style,'list_colors',lambda:{'_palette':{'background':'#111111'}})
    commands=[(f'lk sample{index}','test','Example command') for index in range(30)]
    sent=Mock();keys=iter(keys)
    namespace={'sys':sys,'_command_rows':lambda:commands,'_read_tty_key':lambda fd:next(keys),
        '_write_command_request':sent,'_c':lambda text,*args:text,'_ansi_clip':lambda text,width:text[:width],
        'termios':SimpleNamespace(tcgetattr=lambda fd:['original'],tcsetattr=Mock(),TCSADRAIN=1),
        'tty':SimpleNamespace(setcbreak=lambda fd:None),
        'shutil':SimpleNamespace(get_terminal_size=lambda default:SimpleNamespace(columns=50,lines=16))}
    exec(compile(ast.Module(body=[function],type_ignores=[]),'commands_screen','exec'),namespace)
    assert namespace['commands_screen']()==0
    sent.assert_called_once_with(f'lk sample{expected}')
    text=output.getvalue()
    assert '\033[38;2;95;175;255m' in text
    assert '\033[38;2;160;160;160m' in text
    assert 'Shift+←/→' in text and 'PgUp/PgDn' in text
