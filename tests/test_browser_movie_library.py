import importlib.util,sys
from pathlib import Path
import pytest
from core import video_library,intent_normalizer
ROOT=Path(__file__).resolve().parents[1]

def load(name):
    spec=importlib.util.spec_from_file_location('movies_'+name,ROOT/name/'server.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def movie(i=0):return {'id':str(i),'node':'owner','path':f'/media/movies/Movie{i}.mkv','title':f'Movie {i:02}','media_type':'video/matroska','bytes':10000000+i}

@pytest.mark.parametrize('phrase',['play a movie from our library','play a new movie','can you play a movie from my library?','play a movie','put on a film'])
def test_generic_movies_never_become_library_title_queries(phrase):
    assert video_library.intent(phrase)['action']=='choose'
    intent=intent_normalizer.normalize(phrase)
    assert intent['kind']=='video' and 'query' not in intent

@pytest.mark.parametrize('phrase',['what movies are available to play?','what movies do we have?','list movies','show me movies from our library'])
def test_movie_listing_is_read_only(phrase):assert video_library.intent(phrase)['action']=='list'

def test_named_movie_path_is_preserved():
    assert video_library.intent('play the Star Wars theatrical movie') is None
    intent=intent_normalizer.normalize('play the Star Wars theatrical movie')
    assert intent['kind']=='video' and intent['query']=='Star Wars theatrical'

def test_compact_catalog_excludes_alerts_software_and_duplicates():
    rows=[movie(),dict(movie(),node='copy'),dict(movie(1),path='/Applications/App.app/Contents/sample.mp4'),
          dict(movie(2),path='/System/Library/Sounds/Basso.aiff',media_type='audio/x-aiff'),dict(movie(3),fabric_hidden_by='user')]
    result=video_library.catalog({'entries':rows})
    assert result['total']==1 and result['entries'][0]['id']=='0'

@pytest.mark.parametrize('surface',['albert','signal-window'])
def test_broad_requests_use_compact_catalog_and_list_selection(monkeypatch,surface):
    module=load(surface);calls=[]
    def fetch(path,*args,**kwargs):calls.append(path);return {'entries':[movie(i) for i in range(12)]}
    monkeypatch.setattr(module,'node_json' if surface=='albert' else '_node_call',fetch)
    if surface=='albert':
        result=module.action('what movies are available to play?',session='test')
        assert result['title']=='Videos in your Fabric library'
        assert len(result['clarification']['choices'])==12
        assert module.action('10',session='test')['type']=='video'
    else:
        picks=module._signal_video_choices('test',listing=True)
        assert len(picks)==10
        assert module._signal_pending_media('test','10')['row']['id']=='9'
    assert calls==['/v1/media/videos']

def test_albert_empty_and_failed_library_do_not_fall_through(monkeypatch):
    module=load('albert')
    monkeypatch.setattr(module,'node_json',lambda *a,**k:{'entries':[]})
    assert module.action('play a movie from our library')['title']=='No videos found'
    def fail(*a,**k):raise TimeoutError('library timeout')
    monkeypatch.setattr(module,'node_json',fail)
    assert module.action('play a movie from our library')['title']=='Video library unavailable'

@pytest.mark.parametrize('surface',['albert','signal-window'])
def test_new_named_play_replaces_pending_choices(monkeypatch,surface):
    module=load(surface)
    def fetch(path,*args,**kwargs):
        if path=='/v1/media/videos':return {'entries':[movie(i) for i in range(3)]}
        assert path=='/v1/media/route'
        assert args[0]['query']=='Star Wars theatrical'
        assert args[0]['kind']=='video'
        return {'queue':[movie(42)]}
    monkeypatch.setattr(module,'node_json' if surface=='albert' else '_node_call',fetch)
    if surface=='albert':
        module.action('play a movie from our library',session='switch')
        assert module.action('play the Star Wars theatrical movie',session='switch')['type']=='video'
    else:
        module._signal_video_choices('switch')
        assert module._signal_pending_media('switch','play the Star Wars theatrical movie') is None
        assert 'switch' not in module._SIGNAL_PENDING_MEDIA
