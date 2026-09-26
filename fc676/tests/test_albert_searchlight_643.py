from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def test_search_has_control_plane_independent_local_fallback():
    text=(ROOT/'look/lk').read_text()
    assert 'def _direct_searxng_search' in text
    assert 'FCL_SEARXNG_URL' in text
    fabric=text.index('return _fabric_web_search(query)')
    direct=text.index('return _direct_searxng_search(query)')
    hosted=text.index('return _ollama_web_search(query)', direct)
    assert fabric < direct < hosted

def test_failed_forced_search_is_a_machine_failure_not_stdin_fallthrough():
    text=(ROOT/'look/lk').read_text()
    anchor='events.emit("error", stage="search"'
    assert anchor in text
    tail=text[text.index(anchor):text.index(anchor)+900]
    assert 'if one_shot:' in tail
    assert 'return 1' in tail

def test_albert_reports_failed_edge_not_whole_brain():
    text=(ROOT/'albert/server.py').read_text()
    assert 'Live search unavailable' in text
    assert 'Inference unavailable' in text
    assert 'LO engine unavailable' in text
    assert 'I can reach LO, but the live web-search edge failed' in text

def test_qrencode_stays_in_default_utility_set():
    text=(ROOT/'install-look.sh').read_text()
    assert 'mpv qrencode)' in text
