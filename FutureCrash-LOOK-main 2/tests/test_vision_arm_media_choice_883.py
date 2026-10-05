from pathlib import Path
import importlib.util

ROOT=Path(__file__).resolve().parents[1]

def _load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod


def test_macos_remote_capture_has_explicit_foreground_arm_broker():
    fv=(ROOT/'core/fabric_vision.py').read_text()
    node=(ROOT/'core/node.py').read_text()
    lk=(ROOT/'look/lk').read_text()
    assert 'def run_vision_broker(' in fv
    assert 'def vision_broker_request(' in fv
    assert 'vision-arm.sock' in fv
    assert 'os.chmod(path,0o600)' in fv
    assert 'vision_broker_request' in node
    assert 'capture_authority' in node and 'foreground-arm' in node
    assert 'def _vision_arm_command(' in lk
    assert 'lk vision arm [10m]' in lk
    assert 'Ctrl-C disarms' in lk


def test_typed_video_ambiguity_is_ranked_for_playback_not_exposed_as_exact_error():
    lk=(ROOT/'look/lk').read_text()
    block=lk[lk.index('typed_query=str(intent.get("query") or "").strip()'):lk.index('match_kind,rows=_media_query_matches', lk.index('typed_query=str(intent.get("query") or "").strip()'))]
    assert 'ranked_typed=media_core.rank_entries' in block
    assert 'return [ranked_typed[0][0]],shuffle' in block
    assert 'use --exact' not in block


def test_multiword_video_language_remains_typed():
    normalizer=_load('intent_883',ROOT/'core/intent_normalizer.py')
    result=normalizer.resolve('play catalina shark video')
    assert result['status']=='resolved'
    assert result['intent']['kind']=='video'
    assert result['intent']['query'].casefold()=='catalina shark'
