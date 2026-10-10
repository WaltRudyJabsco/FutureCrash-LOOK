import os

import pytest
from look import notebook
from test_notebook_interaction import lk, terminal


@pytest.mark.parametrize('encoded,expected',[
    (b'\x1b[1;3D','wordleft'),(b'\x1b[1;3C','wordright'),
    (b'\x1b[1;5D','wordleft'),(b'\x1b[1;5C','wordright'),
    (b'\x1bb','wordleft'),(b'\x1bf','wordright'),
    (b'\x1b[1;3A','paragraphup'),(b'\x1b[1;3B','paragraphdown'),
    (b'\x1b[1;2A','shiftup'),(b'\x1b[1;2B','shiftdown')])
def test_modifier_decoder_preserves_shift_pages(encoded,expected):
    read_fd,write_fd=os.pipe()
    try:
        os.write(write_fd,encoded)
        assert lk._read_tty_key(read_fd,.1)==expected
    finally:os.close(read_fd);os.close(write_fd)


@pytest.mark.parametrize('text,cursor,direction,expected',[
    ('alpha beta',10,-1,6),('alpha beta',6,-1,0),
    ('alpha beta',0,1,5),('alpha beta',5,1,10),
    ('cafe\u0301 世界',5,-1,0),('cafe\u0301 世界',0,1,5),
    ('foo/bar_baz',11,-1,4),('foo/bar_baz',4,-1,3),
    ('   ',3,-1,0),('',0,1,0)])
def test_word_boundaries_include_unicode_and_punctuation(text,cursor,direction,expected):
    assert notebook.word_cursor(text,cursor,direction)==expected


def test_editor_word_jumps_and_paragraph_jumps_edit_exact_positions(terminal):
    keys=iter(['wordleft','X','shiftleft','wordright','Y','\x13'])
    assert notebook.capture_note(5,lambda *args:next(keys),'alpha beta')=='alphaY Xbeta'
    text='first line\ncontinuation\n \t\nsecond para\n\nthird'
    starts=[0,text.index('second'),text.index('third'),len(text)]
    assert notebook.paragraph_cursor(text,starts[2]+2,-1)==starts[2]
    assert notebook.paragraph_cursor(text,starts[2],-1)==starts[1]
    assert notebook.paragraph_cursor(text,starts[0],1)==starts[1]
    keys=iter(['paragraphup','X','paragraphup','paragraphup','Y','\x13'])
    result=notebook.capture_note(5,lambda *args:next(keys),text)
    assert result==text[:starts[1]]+'Y'+text[starts[1]:starts[2]]+'X'+text[starts[2]:]


def test_paragraph_endpoints_and_whitespace_only_separators():
    text='one\n\n \t\n\n two\n\n'
    assert notebook.paragraph_cursor(text,0,-1)==0
    assert notebook.paragraph_cursor(text,0,1)==text.index(' two')
    assert notebook.paragraph_cursor(text,len(text),1)==len(text)
