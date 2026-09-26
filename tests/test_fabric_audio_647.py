from pathlib import Path
import importlib.util

ROOT=Path(__file__).resolve().parents[1]


def test_release_and_audio_capability_contract():
    assert (ROOT/'VERSION').read_text().strip()=='6.7.3'
    node=(ROOT/'core/node.py').read_text()
    assert 'RELEASE_NAME = "HOME BASE"' in node
    assert '"audio.speak"' in node
    assert 'if path == "/v1/audio/speak"' in node
    assert 'voice_profile must be default or wopr' in node
    assert 'espeak-ng' in node and 'pitch -250 chorus' in node


def test_cross_platform_install_gets_same_wopr_voice_dependencies():
    install=(ROOT/'install-look.sh').read_text()
    assert 'core+=(sox espeak-ng)' in install
    assert '[[ "$(uname -s)" == "Linux" ]] && core+=(espeak-ng)' not in install


def test_games_use_fabric_speech_first_and_same_local_pipeline():
    games=(ROOT/'look/games.py').read_text()
    assert 'http://127.0.0.1:7332/v1/audio/speak' in games
    assert '"voice_profile":"wopr"' in games
    assert 'pitch -250 chorus 0.6 0.9 55 0.4 0.25 2 -t' in games
    assert 'SHALL WE PLAY A GAME?' in games
    assert 'def wopr_outcome' in games


def test_shared_lo_exposes_audio_speak_tool():
    look=(ROOT/'look/lk').read_text()
    assert '"name":"audio_speak"' in look
    assert 'Speech is a local effect routed to the requested physical node' in look
    assert '"audio_speak":("all","action")' in look
    assert 'SPEAK OK' in look

def test_gtnw_gets_one_sparse_spoken_verdict_hook():
    look=(ROOT/'look/lk').read_text()
    assert 'SOMETIMES THE BEST MOVE IS NOT TO PLAY' in look
    assert 'verdict_spoken' in look
