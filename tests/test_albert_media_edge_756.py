from pathlib import Path
import importlib.util
import sys

ROOT=Path(__file__).resolve().parents[1]


def _server():
    path=ROOT/'albert'/'server.py'
    spec=importlib.util.spec_from_file_location('albert_server_756',path)
    mod=importlib.util.module_from_spec(spec); sys.modules[spec.name]=mod; spec.loader.exec_module(mod)
    return mod


def test_albert_prepared_library_media_becomes_browser_player(monkeypatch):
    a=_server()
    class Engine:
        @staticmethod
        def route_intent(_q): return 'general'
    monkeypatch.setattr(a,'_load_lo_engine',lambda: Engine())
    monkeypatch.setattr(a,'node_json',lambda path,payload=None,timeout=1.25: {
        'ok':True,'node':'3090','state':'prepared','queue':[{
            'id':'song-1','title':'London Calling','artist':'The Clash',
            'album':'London Calling','media_type':'audio/flac','node':'3090'
        }]
    })
    result=a.action('play some clash')
    assert result['type']=='audio'
    assert result['title']=='London Calling'
    assert result['src'].startswith('/v1/media/item?')
    assert 'song-1' in result['src']
    assert result['pipeline']['effect']=='browser playback'


def test_albert_media_proxy_preserves_range_support_contract():
    text=(ROOT/'albert'/'server.py').read_text()
    assert 'def _proxy_media_item' in text
    assert 'handler.headers.get("Range")' in text
    assert "if path=='/v1/media/item':" in text


def test_shared_media_edge_repairs_some_only_after_full_query():
    text=(ROOT/'look'/'lk').read_text()
    marker='Human playback language often uses "some X"'
    assert marker in text
    block=text[text.index(marker)-180:text.index(marker)+900]
    assert '_media_query_matches(text' in block
    assert 'text.casefold().startswith("some ")' in block
    assert 'text[5:].strip()' in block
