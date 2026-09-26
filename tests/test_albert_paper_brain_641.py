from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def test_release_is_paper_brain():
    assert (ROOT/'VERSION').read_text().strip() == '6.7.3'
    node=(ROOT/'core/node.py').read_text()
    assert 'VERSION = "6.7.3"' in node
    assert 'RELEASE_NAME = "HOME BASE"' in node


def test_albert_beacon_and_continuing_fold_ui():
    html=(ROOT/'albert/index.html').read_text()
    assert "fetch('/v1/lights'" in html
    assert 'beacon-layer' in html
    assert 'continue this thought' in html
    assert 'replyFold' in html
    assert 'targetFold' in html


def test_albert_paste_uses_artifact_edge():
    html=(ROOT/'albert/index.html').read_text()
    server=(ROOT/'albert/server.py').read_text()
    assert "addEventListener('paste'" in html
    assert "fetch('/v1/artifacts'" in html
    assert 'context:{...context,session,artifacts:attachmentIds}' in html
    assert "path=='/v1/artifacts'" in server
    assert 'artifact://sha256/' in server
    assert 'selected_paths=selected' in server


def test_albert_uses_shared_router_for_live_search():
    engine=(ROOT/'look/lo_engine.py').read_text()
    core=(ROOT/'look/lk').read_text()
    server=(ROOT/'albert/server.py').read_text()
    assert 'def route_intent(prompt: str)' in engine
    assert 'def _lo_requires_live_web(prompt):' in core
    assert 'turn_route=_lo_cognition_route(prompt,use_openjev=True)' in core
    assert 'turn_force_search=bool(force_search or turn_intent=="web_current")' in core
    assert 'force_search=False' in server
    assert 'shared_intent=_load_lo_engine().route_intent(q)' in server
