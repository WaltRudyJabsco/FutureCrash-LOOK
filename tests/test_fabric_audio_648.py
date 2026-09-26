from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def test_service_binary_discovery_includes_linuxbrew():
    src=(ROOT/'core/node.py').read_text()
    assert 'Path("/home/linuxbrew/.linuxbrew/bin")/name' in src
    assert 'Path.home()/".linuxbrew/bin"/name' in src

def test_sound_check_release_contract():
    assert (ROOT/'VERSION').read_text().strip() == '6.6.3'
    node=(ROOT/'core/node.py').read_text()
    assert 'VERSION = "6.6.3"' in node
    assert 'RELEASE_NAME = "MOVIE NIGHT"' in node
