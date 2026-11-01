import json
from pathlib import Path
import subprocess
from unittest.mock import Mock

import book_audio
import book_speech as speech
from test_book_speech import fixture
from test_media_request_regressions import lk


def test_duplicate_macos_voice_ids_are_removed(tmp_path,monkeypatch):
    monkeypatch.setattr(Path,'home',lambda:tmp_path)
    monkeypatch.setattr(speech.book_reader,'binary',lambda name:'/tools/say' if name=='say' else None)
    monkeypatch.setattr(speech.subprocess,'run',lambda *a,**k:Mock(stdout='Jamie (Premium) en_GB # One\nSamantha (English (US)) en_US # Two\nSamantha (English (US)) en_US # Two\n'))
    assert [row['id'] for row in speech.voices()]==['say:Jamie (Premium)','say:Samantha (English (US))']


def test_voice_cycle_wraps_and_default_restores_original_choice(tmp_path,monkeypatch,lk,capsys):
    monkeypatch.setattr(Path,'home',lambda:tmp_path)
    available=[{'id':'say:Jamie (Premium)','name':'Jamie (Premium)','engine':'say'}, {'id':'say:Samantha','name':'Samantha','engine':'say'}]
    monkeypatch.setattr(speech,'voices',lambda:available)
    monkeypatch.setattr(speech.sys,'stdin',Mock(fileno=lambda:0))
    keys=iter(['v','v','v','V','q']);monkeypatch.setattr(lk,'_read_tty_key',lambda *a:next(keys))
    monkeypatch.setattr(speech.subprocess,'Popen',Mock(side_effect=AssertionError('Voice selection must not start stopped speech')))
    speech.desk(lk,fixture(tmp_path/'book.epub'))
    output=lk._strip_ansi(capsys.readouterr().out)
    assert output.count('voice 1/2')>=3 and 'voice 2/2' in output
    assert 'P clipboard' in output and 'V default voice' in output
    assert speech.preferences()['voice']==''


def test_read_aloud_wraps_complete_paragraphs_and_scrolls(tmp_path,monkeypatch,lk,capsys):
    monkeypatch.setattr(Path,'home',lambda:tmp_path)
    monkeypatch.setattr(speech,'chapters',lambda path:[{'title':'Chapter','paragraphs':['A long passage. '*100+'FINAL WORDS']}])
    path=tmp_path/'book.epub';path.write_bytes(b'fixture')
    monkeypatch.setattr(speech,'voices',lambda:[{'id':'say:Daniel','name':'Daniel','engine':'say'}])
    monkeypatch.setattr(speech.sys,'stdin',Mock(fileno=lambda:0))
    import os
    monkeypatch.setattr(lk.shutil,'get_terminal_size',lambda *a:os.terminal_size((60,24)))
    keys=iter(['pagedown','pagedown','q']);monkeypatch.setattr(lk,'_read_tty_key',lambda *a:next(keys))
    speech.desk(lk,path)
    output=lk._strip_ansi(capsys.readouterr().out)
    assert 'FINAL WORDS' in output
    assert all(len(line)<=60 for line in output.splitlines() if line and not line.startswith('READ ALOUD'))


def test_browser_voice_selection_is_validated_and_cached_separately(tmp_path,monkeypatch):
    monkeypatch.setattr(Path,'home',lambda:tmp_path)
    voices=[{'id':'say:First','name':'First','engine':'say'}, {'id':'say:Second','name':'Second','engine':'say'}]
    monkeypatch.setattr(speech,'voices',lambda:voices);book_audio._voices.cache_clear()
    monkeypatch.setattr(speech.book_reader,'binary',lambda name:'/tools/'+name)
    calls=[]
    def run(args,**kwargs):
        calls.append(args)
        target=Path(args[args.index('-o')+1]) if args[0].endswith('/say') else Path(args[-1])
        target.write_bytes(b'fixture')
    monkeypatch.setattr(book_audio.subprocess,'run',run)
    try:
        a=book_audio.render('Text','book',0,0,'say:First');b=book_audio.render('Text','book',0,0,'say:Second')
        assert a!=b and len(calls)==4
        assert book_audio.render('Text','book',0,0,'say:Second')==b and len(calls)==4
        import pytest
        with pytest.raises(ValueError,match='not installed'):book_audio.render('Text','book',0,0,'arbitrary; command')
        assert not speech.preferences()
    finally:book_audio._voices.cache_clear()


def test_speed_values_are_bounded_and_piper_playback_uses_rate(monkeypatch):
    assert [speech.reading_speed(value) for value in (-5,9,float('nan'),'broken')]==[.5,2,1,1]
    player=speech.Speech({'engine':'piper'},rate=round(speech.DEFAULT_RATE*1.5))
    player.proc=Mock();player.proc.poll.return_value=0;player.phase='preparing'
    monkeypatch.setattr(speech.book_reader,'binary',lambda name:'/tools/'+name)
    launch=Mock();monkeypatch.setattr(player,'launch',launch)
    try:
        player.poll()
        assert any(arg.startswith('--speed=1.49') or arg.startswith('--speed=1.50') for arg in launch.call_args.args[0])
        assert '--audio-pitch-correction=yes' in launch.call_args.args[0]
    finally:player.close()


def test_read_aloud_clears_kitty_cover_before_its_first_text_frame(tmp_path,monkeypatch,lk,capsys):
    monkeypatch.setattr(Path,'home',lambda:tmp_path)
    monkeypatch.setenv('KITTY_WINDOW_ID','fixture')
    monkeypatch.setattr(speech,'voices',lambda:[{'id':'say:Daniel','name':'Daniel','engine':'say'}])
    monkeypatch.setattr(speech.sys,'stdin',Mock(fileno=lambda:0))
    monkeypatch.setattr(lk,'_read_tty_key',lambda *args:'esc')
    speech.desk(lk,fixture(tmp_path/'book.epub'))
    output=capsys.readouterr().out
    assert output.index('\x1b_Ga=d,d=a,q=2\x1b\\') < output.index('READ ALOUD')
