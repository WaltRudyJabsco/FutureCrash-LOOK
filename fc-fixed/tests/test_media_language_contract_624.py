from core import intent_normalizer
from look import media_core


def _library():
    return {"entries":[
        {"path":"/media/TV/The_Mighty-Boosh/01_-_Mutants.avi","artist":"The Mighty Boosh","album":"TV","title":"Mutants","media_type":"video/x-msvideo"},
        {"path":"/media/Music/Blur/02_-_Song_2.flac","artist":"Blur","album":"Blur","title":"Song 2","media_type":"audio/flac"},
        {"path":"/media/Music/X/A Song for You.mp3","artist":"X","album":"Y","title":"A Song for You","media_type":"audio/mpeg"},
    ]}


def test_a_song_is_selector_not_catalog_text():
    got=intent_normalizer.normalize("play a song")
    assert got["kind"]=="audio"
    assert got["selection"]=="random"
    assert got["match_mode"]=="selector"
    assert "query" not in got


def test_quoted_conversational_target_is_literal():
    got=intent_normalizer.normalize('play "Song 2"')
    assert got["query"]=="Song 2"
    assert got["match_mode"]=="literal"


def test_plain_named_target_is_fuzzy_by_default():
    got=intent_normalizer.normalize("play mighty boosh mutants")
    assert got["query"]=="mighty boosh mutants"
    assert got["match_mode"]=="fuzzy"


def test_filename_normalization_ignores_extension_dash_underscore_and_case():
    lib=_library()
    ranked=media_core.rank_entries(lib,"01 mutants",limit=3)
    assert ranked and ranked[0][0]["title"]=="Mutants"
    ranked=media_core.rank_entries(lib,"the mighty boosh mutants",limit=3)
    assert ranked and ranked[0][0]["title"]=="Mutants"


def test_exact_lookup_accepts_title_or_filename_but_not_semantic_guessing():
    lib=_library()
    assert media_core.exact_entries(lib,"Song 2")[0]["title"]=="Song 2"
    assert media_core.exact_entries(lib,"02_-_Song_2.flac")[0]["title"]=="Song 2"
    assert media_core.exact_entries(lib,"song")==[]
