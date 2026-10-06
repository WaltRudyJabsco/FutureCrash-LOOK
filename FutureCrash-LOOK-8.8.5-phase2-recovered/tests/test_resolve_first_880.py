from pathlib import Path
import importlib.util

ROOT=Path(__file__).resolve().parents[1]


def _load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod


def test_media_language_becomes_typed_before_execution():
    normalizer=_load('intent_880',ROOT/'core/intent_normalizer.py')
    stones=normalizer.normalize('play some stones')
    assert stones == {'schema':'fabric-intent-v2','action':'media.play','kind':'audio','artist':'stones','selection':'random','limit':8}
    catalina=normalizer.normalize('play catalina video')
    assert catalina['query']=='catalina' and catalina['kind']=='video'
    assert normalizer.normalize('play video catalina')['query']=='catalina'


def test_unique_artist_suffix_expands_without_guessing():
    media=_load('media_core_880',ROOT/'look/media_core.py')
    lib={'entries':[
        {'artist':'The Rolling Stones','title':'Start Me Up','media_type':'audio/flac','path':'/a.flac'},
        {'artist':'The Rolling Stones','title':'Gimme Shelter','media_type':'audio/flac','path':'/b.flac'},
        {'artist':'Stone Temple Pilots','title':'Plush','media_type':'audio/flac','path':'/c.flac'},
    ]}
    rows=media.select_entries(lib,kind='audio',artist='stones',selection='all')
    assert len(rows)==2 and {r['artist'] for r in rows}=={'The Rolling Stones'}
    ambiguous={'entries':lib['entries']+[{'artist':'The Blue Stones','title':'X','media_type':'audio/flac','path':'/d.flac'}]}
    assert media.select_entries(ambiguous,artist='stones')==[]


def test_vision_has_inventory_and_selected_display_transport():
    fv=(ROOT/'core/fabric_vision.py').read_text()
    node=(ROOT/'core/node.py').read_text()
    lk=(ROOT/'look/lk').read_text()
    assert 'def list_displays()' in fv
    assert '"-D", str(display.get("index") or 1)' in fv
    assert 'cmd.extend(["-o",str(display.get("capture_id"))])' in fv
    assert '/v1/vision/displays' in node
    assert '"display":str(display or "main")' in node
    assert 'lk vision displays [@NODE]' in lk
    assert 'token=="--display"' in lk
    assert 'token=="--displays"' in lk
    assert 'token=="--all"' in lk
    assert 'watch accepts one display' in lk


def test_query_kind_is_enforced_before_player_launch():
    lk=(ROOT/'look/lk').read_text()
    block=lk[lk.index('def _media_tool_play('):lk.index('def _media_tool_queue(',lk.index('def _media_tool_play('))]
    assert 'if kind_filter in {"audio","video"}' in block
    assert 'startswith(kind_filter+"/")' in block
    assert 'MEDIA PLAY FAILED · {label}' in block
