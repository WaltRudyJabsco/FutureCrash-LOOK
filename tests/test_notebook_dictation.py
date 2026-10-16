from unittest.mock import Mock
import pytest
from look import notebook as nb, transcription as speech
from look.notebook_core import Notebook

@pytest.fixture
def terminal(monkeypatch):
    monkeypatch.setattr(nb.termios,'tcgetattr',lambda fd:['previous'])
    monkeypatch.setattr(nb.termios,'tcsetattr',Mock())
    monkeypatch.setattr(nb.tty,'setraw',Mock())
    monkeypatch.setattr(nb.tty,'setcbreak',Mock())


def test_dictation_inserts_at_caret_and_editor_keeps_working(terminal,monkeypatch,capsys):
    monkeypatch.setattr(speech,'dictate',lambda:'café\nsecond')
    keys=iter(['left']*4+['\x04','D','\x13'])
    assert nb.capture_note(5,lambda *a:next(keys),'Before tail')=='Before café\nsecond Dtail'
    import re
    output=re.sub(r'\x1b\[[0-9;]*m','',capsys.readouterr().out)
    assert 'Ctrl-D dictate' in output and 'Ctrl-C finishes' in output
    assert '\x1b[?2004l\x1b[<u' in output
    assert nb.tty.setraw.call_count>=2

@pytest.mark.parametrize('error',[ValueError('Run lk transcribe setup'),KeyboardInterrupt()])
def test_failed_or_cancelled_dictation_keeps_draft(terminal,monkeypatch,error):
    def fail():raise error
    monkeypatch.setattr(speech,'dictate',fail)
    keys=iter(['\x04','\x13'])
    assert nb.capture_note(5,lambda *a:next(keys),'Keep this draft')=='Keep this draft'
    assert nb.tty.setraw.call_count>=2


def test_escape_after_dictation_does_not_save_note(terminal,monkeypatch,tmp_path):
    store=Notebook(tmp_path);store.create('Original note');row=store.list()[0]
    monkeypatch.setattr(speech,'dictate',lambda:'Added words')
    keys=iter(['\x04','esc'])
    assert nb.quick_edit(store,row,5,lambda *a:next(keys))==''
    assert store.list()[0]['revision']==row['revision']


def test_capital_d_and_paste_never_start_microphone(terminal,monkeypatch):
    microphone=Mock();monkeypatch.setattr(speech,'dictate',microphone)
    keys=iter(['D','paste:\x04words','\x13'])
    assert nb.capture_note(5,lambda *a:next(keys))=='D\\x04words'
    microphone.assert_not_called()

@pytest.mark.parametrize('text,cursor,spoken,expected',[
    ('one two',4,'three','one three two'),('one.',3,'two','one two.'),
    ('Hello',5,'','Hello'),('a\nb',2,'界','a\n界 b')])
def test_spacing_preserves_surrounding_text(text,cursor,spoken,expected):
    result,position=nb.insert_dictation(text,cursor,spoken)
    assert result==expected and 0<=position<=len(result)
