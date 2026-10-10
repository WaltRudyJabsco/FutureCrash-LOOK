import re

from look.notebook_markdown import cell_width, render


def plain(rows):
    return [re.sub(r'\033\[[0-9;]*m','',row).rstrip() for row in rows]


def test_headings_hide_opening_and_closing_marks_and_distinguish_levels():
    rows=render('# Main #\n## Section ##\n### Detail\n#### Small',40)
    assert plain(rows)==['Main','Section','Detail','Small']
    assert '\033[0;1;38;5;117m' in rows[0]
    assert '\033[0;38;5;117m' in rows[2]
    assert ';2m' in rows[3]


def test_inline_formatting_and_literal_escaped_marks():
    rows=render('**bold** *italic* ~~old~~ `**literal**` \\*star\\* snake_case',80)
    assert plain(rows)==['bold italic old **literal** *star* snake_case']
    for code in ('1','3','9','38;5;180'): assert '\033[0;'+code+'m' in rows[0]


def test_nested_formatting_and_unmatched_marks():
    rows=render('**bold and *italic* inside**\nUnfinished **bold',80)
    assert plain(rows)==['bold and italic inside','Unfinished **bold']
    assert '\033[0;1;3m' in rows[0]
    assert plain(render('***both*** and ___also both___',40))==['both and also both']


def test_tasks_bullets_numbered_lists_quotes_and_links():
    assert plain(render('- [ ] Milk\n- [x] Done\n* Item\n2. Next\n> **Quote**\n[Site](https://example.com)',80))==[
        '☐ Milk','☑ Done','• Item','2. Next','│ Quote','Site']


def test_fenced_code_retains_marks_and_hides_fences():
    assert plain(render('```md\n# literal **code**\n```\n# Heading',40))==[
        '# literal **code**','Heading']
    assert plain(render('~~~\n**literal**\n~~~',40))==['**literal**']


def test_setext_headings_and_rule():
    assert plain(render('Title\n=====\n\n---',10))==['Title','','──────────']


def test_wrapping_ignores_ansi_and_respects_unicode_cell_width():
    rows=render('**hello world**\n界界 e\u0301\n'+('x'*40),7)
    assert plain(rows)[:2]==['hello','world']
    for row in rows:
        text=re.sub(r'\033\[[0-9;]*m','',row)
        assert sum(cell_width(char) for char in text)==7


def test_narrow_boxes_and_terminal_controls():
    assert plain(render('界',1))==['�']
    assert '\033[2J' not in ''.join(render('\033[2Jtext\x00',20))
    assert plain(render('',20))==[]
