import json
from pathlib import Path
import signal
import zipfile
from unittest.mock import Mock
import pytest
import book_speech as speech
from test_media_request_regressions import lk


def fixture(path):
    with zipfile.ZipFile(path,'w') as z:
        z.writestr('META-INF/container.xml','<container><rootfile full-path="OPS/book.opf"/></container>')
        z.writestr('OPS/book.opf','<package><manifest><item id="a" href="one.xhtml"/><item id="b" href="two.xhtml"/></manifest><spine><itemref idref="a"/><itemref idref="b"/></spine></package>')
        z.writestr('OPS/one.xhtml','<html><head><title>Skip head</title><script>not spoken</script></head><body><h1>Chapter One</h1><p>Café &amp; books.</p><p>Second <b>passage</b>.</p></body></html>')
        z.writestr('OPS/two.xhtml','<h1>Chapter Two</h1><p>Another passage.</p>')
    return path


def test_epub_spine_order_paragraphs_and_markup(tmp_path):
    rows=speech.chapters(fixture(tmp_path/'book.epub'))
    assert [r['title'] for r in rows]==['Chapter One','Chapter Two']
    assert rows[0]['paragraphs']==['Chapter One','Café & books.','Second passage.']


def test_book_extraction_rejects_oversized_chapter(tmp_path,monkeypatch):
    monkeypatch.setattr(speech,'MAX_CHAPTER_BYTES',10)
    with pytest.raises(ValueError,match='exceeds'):speech.chapters(fixture(tmp_path/'book.epub'))


def test_voice_preference_is_discovered_and_user_choice_wins(tmp_path,monkeypatch):
    monkeypatch.setattr(Path,'home',lambda:tmp_path)
    rows=[{'id':'say:Daniel','engine':'say','locale':'en_GB'}, {'id':'say:Jamie (Premium)','engine':'say','locale':'en_GB'}]
    assert speech.preferred_voice(rows)==rows[1]
    speech.preferences(voice='say:Daniel');assert speech.preferred_voice(rows)==rows[0]


def test_speech_pause_stop_only_own_process_and_pass_text_as_file(tmp_path,monkeypatch):
    monkeypatch.setattr(speech.book_reader,'binary',lambda name:'/tools/'+name)
    process=Mock(pid=123456);process.poll.return_value=None
    launch=Mock(return_value=process);monkeypatch.setattr(speech.subprocess,'Popen',launch)
    signals=[];monkeypatch.setattr(speech.os,'killpg',lambda pid,sig:signals.append((pid,sig)))
    voice={'engine':'say','name':'Jamie (Premium)'};player=speech.Speech(voice)
    try:
        player.start('Café $(do not execute)')
        args=launch.call_args.args[0]
        assert args[:3]==['/tools/say','-v','Jamie (Premium)']
        assert Path(args[-1]).read_text()=='Café $(do not execute)'
        assert launch.call_args.kwargs['stdin']==speech.subprocess.DEVNULL
        player.pause();assert player.paused
        player.pause();assert not player.paused
        player.stop();assert all(pid==process.pid for pid,_ in signals)
        assert [sig for _,sig in signals]==[signal.SIGSTOP,signal.SIGCONT,signal.SIGCONT,signal.SIGTERM]
        process.wait.assert_called_once()
    finally:player.close()


def test_read_aloud_resumes_and_selects_mid_chapter_without_starting_audio(tmp_path,monkeypatch,lk):
    monkeypatch.setattr(Path,'home',lambda:tmp_path)
    monkeypatch.setattr(speech,'voices',lambda:[{'id':'say:Daniel','name':'Daniel','engine':'say','locale':'en_GB'}])
    keys=iter(['down','esc']);monkeypatch.setattr(lk,'_read_tty_key',lambda *args:next(keys))
    class Input:
        def fileno(self):return 0
    monkeypatch.setattr(speech.sys if hasattr(speech,'sys') else __import__('sys'),'stdin',Input())
    monkeypatch.setattr(speech.subprocess,'Popen',lambda *a,**k:pytest.fail('selection must not start audio'))
    source=fixture(tmp_path/'book.epub')
    speech.desk(lk,source,chapter=1,paragraph=2)
    value=json.loads((tmp_path/'.local/share/look/book-speech/positions.json').read_text())
    assert value[speech.book_core.digest(source)]=={'chapter':0,'paragraph':2}
