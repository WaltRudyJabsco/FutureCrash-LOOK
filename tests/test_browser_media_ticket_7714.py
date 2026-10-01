from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_signal_catalog_id_beats_digest_and_uses_ticket():
    js = (ROOT / 'signal-window/app.js').read_text()
    assert "const itemId=String(entry?.id||'')" in js
    assert "if(itemId){qs=new URLSearchParams({kind:'audio'" in js
    assert "else if(digest){qs=new URLSearchParams({kind:'artifact'" in js
    assert "fetch('/api/media/ticket?'" in js
    assert 'browserElement.src=await browserMediaUrl(entry,index)' in js


def test_signal_media_ticket_is_scoped_and_does_not_make_media_public():
    py = (ROOT / 'signal-window/server.py').read_text()
    assert 'def _media_ticket_valid' in py
    assert 'if path=="/api/media/ticket": return self._media_ticket_request(parsed)' in py
    assert 'not self._media_ticket_allows(parsed) and not self._require_endpoint(scope)' in py
    assert '_MEDIA_TICKET_TTL = 600' in py


def test_albert_catalog_media_uses_ticketed_item_url():
    py = (ROOT / 'albert/server.py').read_text()
    assert "item_id=str(first.get('id') or '')" in py
    assert "ticket=_media_ticket_issue(media_node,item_id)" in py
    assert "'ticket':ticket" in py
    assert "not _media_ticket_valid(ticket,node,item_id) and not self._require_endpoint('lo.use')" in py


def _load_module(path, name):
    import importlib.util
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_signal_ticket_is_bound_to_exact_media_identity():
    mod = _load_module(ROOT / 'signal-window/server.py', 'signal_ticket_7714')
    key = mod._media_ticket_key('audio', '3090', 'abc123', '', 0)
    token = mod._media_ticket_issue(key)
    assert mod._media_ticket_valid(token, key)
    assert not mod._media_ticket_valid(token, mod._media_ticket_key('audio', '3090', 'other', '', 0))


def test_albert_ticket_is_bound_to_exact_media_identity():
    mod = _load_module(ROOT / 'albert/server.py', 'albert_ticket_7714')
    token = mod._media_ticket_issue('3090', 'abc123')
    assert mod._media_ticket_valid(token, '3090', 'abc123')
    assert not mod._media_ticket_valid(token, '3090', 'other')
