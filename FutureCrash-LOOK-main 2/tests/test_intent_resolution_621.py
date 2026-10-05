from core.intent_normalizer import resolve

def test_resolved_selector():
    r=resolve('play any movie')
    assert r['status']=='resolved'
    assert r['intent']['kind']=='video'

def test_deictic_media_asks_for_clarification():
    r=resolve('play that movie')
    assert r=={'status':'clarify','reason':'referent_required'}

def test_long_tail_declines_cheaply():
    assert resolve('find something strange I watched last winter')['status']=='no_match'
