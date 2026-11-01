import wave
from types import SimpleNamespace
import pytest
import book_pacing


def test_boundaries_preserve_abbreviations_numbers_quotes_and_word_hyphens():
    parts=book_pacing.segments('Dr. Smith paid 3.14 dollars. “Wait!” He paused—then spoke: at 12:30. A well-known tale.','natural')
    assert parts==[('Dr. Smith paid 3.14 dollars.',350),('“Wait!”',350),('He paused—',200),('then spoke:',200),('at 12:30.',350),('A well-known tale.',350)]
    assert book_pacing.segments('J. R. R. Tolkien wrote the U.S. edition.','natural')==[('J. R. R. Tolkien wrote the U.S. edition.',350)]
    assert book_pacing.segments('In 2010–2015, a well-known tale.','natural')==[('In 2010–2015, a well-known tale.',350)]
    assert book_pacing.segments('Do not split this—please.','voice')==[('Do not split this—please.',0)]
    with pytest.raises(ValueError):book_pacing.segments('Text.','unbounded')
    assert len(book_pacing.segments('One. '*1000,'relaxed'))<=book_pacing.MAX_SEGMENTS


def test_engine_markup_is_generated_without_accepting_book_commands():
    assert '[[slnc 350]]' in book_pacing.say_text('Hello.','natural')
    assert '[[rate' not in book_pacing.say_text('[[rate 500]] Hello.','natural')
    text=book_pacing.espeak_text('<voice>Hello:</voice> world.','relaxed')
    assert '&lt;voice&gt;' in text and '<break time="350ms"/>' in text and '<voice>' not in text


def test_piper_loads_once_and_inserts_frame_aligned_silence(tmp_path):
    loaded=[]
    def voice_loader(model):
        loaded.append(model)
        return SimpleNamespace(synthesize=lambda text:[SimpleNamespace(sample_rate=22050,sample_width=2,sample_channels=1,audio_int16_bytes=b'\x01\x00'*10)])
    path=tmp_path/'paced.wav'
    book_pacing.piper_wave('fixture',[('One.',350),('Two—',200)],path,voice_loader)
    assert loaded==['fixture']
    with wave.open(str(path)) as reader:
        assert reader.getnframes()==20+7718+4410
        assert reader.readframes(10)==b'\x01\x00'*10
        assert reader.readframes(7718)==bytes(7718*2)


def test_pause_profile_has_its_own_cache_and_safe_mac_input(tmp_path,monkeypatch):
    import book_audio
    from pathlib import Path
    monkeypatch.setattr(Path,'home',lambda:tmp_path)
    monkeypatch.setattr(book_audio,'_voices',lambda minute:[{'id':'say:fixture','name':'Fixture','engine':'say'}])
    monkeypatch.setattr(book_audio.book_speech.book_reader,'binary',lambda name:'/tools/'+name)
    inputs=[]
    def run(args,**kw):
        if '-o' in args:
            inputs.append(Path(args[args.index('-f')+1]).read_text());Path(args[args.index('-o')+1]).write_bytes(b'wave')
        else:Path(args[-1]).write_bytes(b'aac')
    monkeypatch.setattr(book_audio.subprocess,'run',run)
    plain=book_audio.render('Hello. World.','fixture',0,0,'say:fixture')
    paced=book_audio.render('Hello. World.','fixture',0,0,'say:fixture','natural')
    assert plain!=paced and inputs==['Hello. World.','Hello. [[slnc 350]] World. [[slnc 350]]']
    assert book_audio.render('Hello. World.','fixture',0,0,'say:fixture','natural')==paced
    assert len(inputs)==2
    with pytest.raises(ValueError):book_audio.render('Hello.','fixture',0,0,'say:fixture','bad')


def test_book_audio_api_passes_pause_profile(tmp_path,monkeypatch):
    from unittest.mock import Mock
    import book_core,book_audio
    from core import node
    from test_book_speech import fixture
    shelf=book_core.Shelf(tmp_path/'state.json',tmp_path/'library')
    book=shelf.import_file(fixture(tmp_path/'seed.epub'))
    handler=node.API.__new__(node.API)
    handler.path='/v1/books/audio?id='+book['id']+'&voice=fixture&pauses=relaxed'
    handler._file_target=lambda:(None,{})
    handler._books_shelf=lambda:shelf
    handler._serve_file_range=Mock();handler.sendj=Mock()
    render=Mock(return_value=tmp_path/'audio.m4a');monkeypatch.setattr(book_audio,'render',render)
    handler._book_content()
    assert render.call_args.args[-2:]==('fixture','relaxed')
    handler._serve_file_range.assert_called_once_with(tmp_path/'audio.m4a','audio/mp4')
    handler.sendj.assert_not_called()
