from core import intent_normalizer
from look import media_core


def test_any_movie_is_selector_not_literal_query():
    got=intent_normalizer.normalize('play any movie')
    assert got['action']=='media.play'
    assert got['kind']=='video'
    assert got['selection']=='random'
    assert 'query' not in got


def test_plain_named_media_preserves_catalog_query():
    got=intent_normalizer.normalize('play Talking Heads')
    assert got['action']=='media.play'
    assert got['query']=='Talking Heads'
    assert 'kind' not in got


def test_something_by_artist_becomes_structured_artist_selector():
    got=intent_normalizer.normalize('play something by Talking Heads')
    assert got['kind']=='audio'
    assert got['artist']=='Talking Heads'
    assert got['selection']=='random'


def test_media_selector_filters_kind_before_random_choice():
    rows=[
        {'path':'/x/a.mp3','artist':'A','title':'song','media_type':'audio/mpeg'},
        {'path':'/x/b.avi','artist':'','title':'movie','media_type':'video/x-msvideo'},
    ]
    got=media_core.select_entries({'entries':rows},kind='video',selection='random',limit=1,seed=1)
    assert len(got)==1 and got[0]['title']=='movie'


def test_media_tool_translation_keeps_core_structured():
    normalized=intent_normalizer.normalize('play a movie')
    tool=intent_normalizer.media_tool(normalized)
    assert tool=={'tool':'media_play','args':{'kind':'video','selection':'random','limit':1}}


def test_conversational_movie_selectors_do_not_become_catalog_queries():
    for phrase in (
        'play us a movie',
        'play a movie for us',
        'any movie will do',
        'a movie is fine',
        'just some video',
    ):
        got=intent_normalizer.normalize(phrase)
        assert got['action']=='media.play', phrase
        assert got['kind']=='video', phrase
        assert got['selection']=='random', phrase
        assert 'query' not in got, phrase


def test_conversational_audio_selectors_stay_typed_too():
    got=intent_normalizer.normalize('any song will do')
    assert got['action']=='media.play'
    assert got['kind']=='audio'
    assert got['selection']=='random'
    assert 'query' not in got
