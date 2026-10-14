import re
import terminal_style
import disc_ui

STRIP=re.compile(r'\x1b\[[0-9;]*m')
COLORS={'CYAN':'\x1b[36m','GRAY':'\x1b[90m'}


def test_wrapping_preserves_actions_and_case():
    text='W shell pane · b browser · q/Esc exit'
    lines=terminal_style.command_lines(text,24,colors=COLORS)
    plain=[STRIP.sub('',line) for line in lines]
    assert all(len(line)<=24 for line in plain)
    assert ' '.join(plain)==text
    assert '\x1b[36m\x1b[1mW' in ''.join(lines)
    assert '\x1b[36m\x1b[1mb' in ''.join(lines)
    assert '\x1b[90m shell pane' in ''.join(lines)


def test_explicit_tokens_do_not_color_fragments_of_words():
    value=terminal_style.command_text('y yes · mystery · Esc back',['y','Esc'],colors=COLORS)
    assert STRIP.sub('',value)=='y yes · mystery · Esc back'
    assert value.count('\x1b[1m')==2


def test_import_pipe_output_stays_plain(monkeypatch):
    monkeypatch.setattr(disc_ui.sys.stdout,'isatty',lambda:False)
    assert disc_ui.instruction('y start · Esc back')=='y start · Esc back'
