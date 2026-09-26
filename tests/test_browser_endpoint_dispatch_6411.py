from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def test_cli_delegates_browser_speech_resolution_to_resident_daemon():
    src=(ROOT/'core/node.py').read_text()
    assert 'if path == "/v1/endpoints/fabric/dispatch"' in src
    assert '_endpoint_dispatch_fabric(str(d.get("target") or ""),str(d.get("action") or ""),d.get("payload") or {})' in src
    assert '_daemon_post(a.host,a.port,"/v1/endpoints/fabric/dispatch",{"target":a.node,"action":"audio.speak","payload":payload})' in src
    # The CLI must not resolve live browser presence from its own process memory.
    block=src[src.index('if a.command=="speak":'):src.index('if a.command=="media-outputs":')]
    assert 'result=_endpoint_dispatch_fabric(a.node' not in block


def test_release_6411_contract():
    assert (ROOT/'VERSION').read_text().strip()=='6.6.5'
    node=(ROOT/'core/node.py').read_text()
    assert 'VERSION = "6.6.5"' in node
    assert 'RELEASE_NAME = "PICTURE LOCK"' in node
