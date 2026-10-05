from pathlib import Path
import importlib.util

ROOT=Path(__file__).resolve().parents[1]

def _load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod

def test_vision_tls_error_path_imports_ssl():
    node=(ROOT/'core/node.py').read_text()
    assert 'import ssl' in node
    assert 'except ssl.SSLCertVerificationError' in node

def test_remote_paths_cannot_impersonate_local_paths():
    lk=(ROOT/'look/lk').read_text()
    block=lk[lk.index('def _media_entry_source('):lk.index('def _media_wait_for_local_queue(')]
    assert 'if node and str(node).casefold() not in local_names' in block
    assert 'continue' in block

def test_execution_queue_pins_reachable_fabric_locations():
    lk=(ROOT/'look/lk').read_text()
    assert 'def _media_pin_playable_entry(' in lk
    assert 'method="HEAD"' in lk
    assert 'def _media_pin_playable_rows(' in lk
    prepare=lk[lk.index('def _media_prepare_command('):lk.index('def _media_play_command(')]
    assert 'rows,failures=_media_pin_playable_rows(rows)' in prepare
    launch=lk[lk.index('def _media_launch_session('):lk.index('def _media_launch_stream(')]
    assert 'pinned,unreachable=_media_pin_playable_rows(queue)' in launch

def test_typed_multiword_video_stays_deterministic():
    normalizer=_load('intent_882',ROOT/'core/intent_normalizer.py')
    intent=normalizer.normalize('play catalina shark video')
    assert intent['action']=='media.play'
    assert intent['kind']=='video'
    assert intent['query'].casefold()=='catalina shark'
    lk=(ROOT/'look/lk').read_text()
    resolve=lk[lk.index('def _media_resolve_targets('):lk.index('def _media_prepare_command(')]
    assert 'typed_query=str(intent.get("query") or "").strip()' in resolve
    assert 'typed_kind=str(intent.get("kind") or "").casefold()' in resolve
