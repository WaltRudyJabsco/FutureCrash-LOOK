import re
from pathlib import Path

from look import look_renderer as renderer
from look import terminal_style


def colors(line):
    return re.findall(r'\x1b\[38;2;\d+;\d+;\d+m',line)


def test_clipped_multi_span_row_keeps_type_and_metadata_colors():
    line='\x1b[22;23;24m\x1b[38;2;80;120;200mfile.py\x1b[38;2;120;120;120m metadata too long'
    clipped=renderer.fit(line,18)
    assert colors(clipped)==colors(line)
    assert len(renderer.strip_ansi(clipped))==18
    assert clipped.endswith('…'+renderer.RESET)


def test_filter_rows_keep_distinct_file_colors_when_preview_narrows_list(tmp_path):
    (tmp_path/'folder').mkdir()
    for name in ('document.pdf','song.flac','source.py'):(tmp_path/name).write_text('data')
    entries=renderer.read_entries(tmp_path)
    plain=renderer.detail_rows(entries,110)
    selected=renderer.detail_rows(entries,110,tmp_path/'source.py')
    for original,focused in zip(plain,selected):
        if 'source.py' in renderer.strip_ansi(original):
            assert '\x1b[48;2;' in renderer.fit(focused,52)
        else:
            assert colors(renderer.fit(focused,52))==colors(renderer.fit(original,52))
    type_colors=[colors(renderer.fit(row,52))[1] for row in selected]
    assert len(set(type_colors))>=3


def test_clipping_keeps_mark_color_and_stops_without_leaking_highlight():
    line=terminal_style.list_row('\x1b[32m✓\x1b[0m \x1b[34mfolder/ long name',80,0,True)
    clipped=renderer.fit(line,12)
    assert '\x1b[48;2;' in clipped and len(set(colors(clipped)))>=2
    assert clipped.endswith(renderer.RESET)
    assert renderer.fit(line,0)==''
