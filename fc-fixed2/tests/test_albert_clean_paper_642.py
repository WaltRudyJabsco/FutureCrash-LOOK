from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def test_qrencode_is_normal_install_dependency():
    text=(ROOT/'install-look.sh').read_text()
    assert 'mpv qrencode)' in text

def test_fabric_search_precedes_hosted_search():
    text=(ROOT/'look/lk').read_text()
    assert 'def _fabric_web_search' in text
    assert 'def _search_web' in text
    assert 'return _fabric_web_search(query)' in text
    assert 'result = _search_web(prompt)' in text

def test_albert_never_prints_tool_protocol_and_threads_first_answer():
    server=(ROOT/'albert/server.py').read_text()
    ui=(ROOT/'albert/index.html').read_text()
    assert 'def _looks_like_tool_plumbing' in server
    assert 'cognition returned unexecuted tool protocol' in server
    assert "f.turns=[{role:'user',text:context.query},{role:'assistant',text:f.text||''}]" in ui
    assert "function topicTitle(q)" in ui
    assert "startsWith('Fabric cognition')" in ui
