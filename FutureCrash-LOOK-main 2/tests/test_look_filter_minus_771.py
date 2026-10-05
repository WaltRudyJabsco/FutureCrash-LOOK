import importlib.util
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('look_renderer_771',ROOT/'look'/'look_renderer.py')
m=importlib.util.module_from_spec(spec); sys.modules[spec.name]=m; spec.loader.exec_module(m)

def test_positive_filter_contract_is_unchanged():
    assert m.query_matches('Mercury Writer Dark.png','merc dark')
    assert not m.query_matches('Mercury Writer Light.png','merc dark')

def test_negative_terms_subtract_with_same_substring_semantics():
    assert m.query_matches('Mercury Writer Light.png',r'merc \dark')
    assert not m.query_matches('Mercury Writer Dark.png',r'merc \dark')
    assert not m.query_matches('old Mercury Writer.png',r'merc \dark \old')

def test_negative_only_query_works():
    assert m.query_matches('Mercury.png',r'\backup')
    assert not m.query_matches('Mercury backup.png',r'\backup')

def test_backslash_dot_means_dot_prefixed_not_any_dot():
    assert m.query_matches('photo.png',r'\.')
    assert not m.query_matches('.DS_Store',r'\.')
    assert not m.query_matches('.config',r'png \.' )

def test_match_glob_version_tool_remains_separate():
    text=(ROOT/'look'/'lk').read_text()
    assert 'lk match GLOB [v|t|n]' in text
    assert 'if cmd=="match": return _match_command(rest)' in text
