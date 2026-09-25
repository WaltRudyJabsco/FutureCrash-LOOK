from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def test_albert_is_installed_surface():
    assert (ROOT/'albert/index.html').exists()
    s=(ROOT/'install.sh').read_text(); assert 'albert/install.sh' in s
    n=(ROOT/'core/node.py').read_text(); assert '"albert": probe("127.0.0.1", 7330)' in n

def test_albert_action_grammar_and_easter_eggs():
    a=(ROOT/'albert/server.py').read_text(); lk=(ROOT/'look/lk').read_text()
    assert 'fabric-action-registry-v1' in a
    assert 'All Classical Radio' in a and 'Classic Arts Showcase' in a
    assert 'raw in {"classics","classical"}' in lk
    assert 'raw in {"arts","showcase","classic-arts"}' in lk
    assert 'cmd=="albert"' in lk

def test_albert_paper_is_semantic_not_app_shell():
    s=(ROOT/'albert/index.html').read_text()
    for kind in ['answer','audio','video','image','file','watch','route','person','receipt','progress']:
        assert f"f.type==='{kind}'" in s
    assert 'ask, act, paste, or drop' in s

def test_albert_632_uses_shared_cognition_and_session():
    server=(ROOT/'albert/server.py').read_text()
    html=(ROOT/'albert/index.html').read_text()
    assert 'ALBERT_COGNITION_URL' in server
    assert 'http://127.0.0.1:7331/api/chat' in server
    assert 'cognition_json(q, session=session)' in server
    assert 'understood' in server and 'cognition_json(q, session=session)' in server
    assert 'ALBERT_SESSION' in html
    assert "localStorage.getItem('albert-session')" in html
    assert "Fabric cognition is unavailable. I will not invent a result." in html
