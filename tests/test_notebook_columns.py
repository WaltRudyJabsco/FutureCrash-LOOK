import re
import pytest
from look import notebook


def plain(text):return re.sub(r'\033\[[0-9;]*m','',text)
def cells(text):return sum(map(notebook.cell_width,plain(text)))


@pytest.mark.parametrize('width,fields',[(24,['title']),(40,['title','kind']),(80,['title','kind','project']),(140,['title','kind','project'])])
def test_columns_fit_terminal_and_prioritize_title(width,fields):
    rows=[{'project':'A very long project name'}]
    columns=notebook.notebook_columns(width,rows)
    assert [field for field,size in columns]==fields
    assert sum(size for field,size in columns)+notebook.NOTE_COLUMN_GAP*(len(columns)-1)==width-4
    assert columns[0][1]>=max(size for field,size in columns)


@pytest.mark.parametrize('value',['A long title '*20,'界'*50,'café e\u0301 '*30,'plain','two\nlines\tand tabs','\x1b[2J'])
@pytest.mark.parametrize('width',[1,8,23])
def test_column_clipping_and_padding_respect_unicode_cells(value,width):
    output=notebook.column_text(value,width)
    assert cells(output)==width
    assert '\x1b' not in output and '\n' not in output and '\t' not in output


def test_long_titles_do_not_move_type_or_project_columns(monkeypatch):
    monkeypatch.setenv('LOOK_TERMINAL_THEME','paper')
    colors=notebook.terminal_style.list_colors()
    rows=[{'title':'Short','kind':'note','project':'Writing'},
          {'title':'界'*100,'kind':'reminder','project':'Writing'}]
    columns=notebook.notebook_columns(100,rows)
    lines=[plain(notebook.notebook_row(row,colors,columns)) for row in rows]
    for row,line in zip(rows,lines):
        type_offset=line.index(row['kind'])
        project_offset=line.index('Writing')
        assert cells(line[:type_offset])==columns[0][1]+2
        assert cells(line[:project_offset])==columns[0][1]+columns[1][1]+4
        assert cells(line)==96
    assert '…' in lines[1]
