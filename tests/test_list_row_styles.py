import re
import pytest
from look import terminal_style


def plain(value):return re.sub(r'\x1b\[[0-9;]*m','',value)


@pytest.mark.parametrize('theme',('paper','neon','slate'))
def test_selection_retains_alert_and_detail_inks_and_does_not_leak(monkeypatch,theme):
    monkeypatch.setenv('LOOK_TERMINAL_THEME',theme);colors=terminal_style.list_colors()
    line='\033[37mTitle\033[0m · \033[31mfailed\033[0m · \033[2msource\033[0m'
    result=terminal_style.list_row(line,60,0,True,colors)
    assert result.startswith(colors['SELECT_BG']) and result.endswith('\033[0m')
    assert colors['SELECT_RED']+'failed' in result
    assert colors['SELECT_GRAY']+'source' in result
    assert colors['SELECT_RED']!=colors['SELECT_FG']
    assert len(plain(result))==59
    unselected=terminal_style.list_row(line,60,1,False,colors)
    assert colors['SELECT_BG'] not in unselected
    assert plain(unselected)==plain(line)


def test_alternation_is_subtle_and_preserves_file_type_hues(monkeypatch):
    monkeypatch.setenv('LOOK_TERMINAL_THEME','paper');colors=terminal_style.list_colors()
    line='\033[38;5;75m\uf1c9 script.py\033[0m · \033[2m12 KB\033[0m'
    first=terminal_style.list_row(line,80,0,False,colors)
    second=terminal_style.list_row(line,80,1,False,colors)
    assert first!=second and plain(first)==plain(second)==plain(line)
    assert '38;2;25;58;90m' in first


def test_unicode_clipping_and_terminal_controls_are_bounded(monkeypatch):
    monkeypatch.setenv('LOOK_TERMINAL_THEME','paper');colors=terminal_style.list_colors()
    result=terminal_style.list_row('中文e\u0301abc',7,0,True,colors)
    assert plain(result)=='中文e\u0301a'
    result=terminal_style.list_row('name\x07\x1b]0;bad',30,0,False,colors)
    assert '\x07' not in result and '\x1b]' not in result


def test_reset_theme_has_a_working_fallback(monkeypatch):
    monkeypatch.setenv('LOOK_TERMINAL_THEME','reset')
    assert terminal_style.list_row('A file',20,selected=True).endswith('\033[0m')


def test_filesystem_selection_retains_icon_and_metadata_colors(tmp_path,monkeypatch):
    from look import look_renderer as renderer
    monkeypatch.setenv('LOOK_TERMINAL_THEME','paper');colors=terminal_style.list_colors()
    monkeypatch.setattr(renderer,'_LIST_COLORS',colors)
    path=tmp_path/'script.py';path.write_text('print(1)')
    rows=renderer.detail_rows(renderer.read_entries(tmp_path,True),80,path)
    assert '\uf1c9' in plain(rows[0]) and 'script.py' in plain(rows[0])
    assert colors['SELECT_BG'] in rows[0]
    codes=set(re.findall(r'\x1b\[38;2;[^m]*m',rows[0]))
    assert len(codes)>=2
