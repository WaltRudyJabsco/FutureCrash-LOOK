from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def test_albert_ask_returns_durable_media_identity_not_ephemeral_ticket():
    server=(ROOT/'albert/server.py').read_text()
    assert '"media":{"node":media_node,"id":item_id,"index":0}' in server
    action_block=server[server.index("if shared_intent!=\"games\""):server.index("# Anything not handled", server.index("if shared_intent!=\"games\""))]
    assert "ticket=_media_ticket_issue(media_node,item_id)" not in action_block
    assert "src='/api/media/audio?'" not in action_block


def test_albert_browser_mints_ticket_at_playback_time_like_signal():
    html=(ROOT/'albert/index.html').read_text()
    assert 'data-media-id=' in html
    assert 'async function hydrateFabricMedia()' in html
    assert "fetch('/api/media/ticket?'" in html
    assert "media.src=d.url+`&t=${Date.now()}`" in html
    assert 'await hydrateFabricMedia();initAudioEQ()' in html


def test_albert_ticket_endpoint_remains_scoped_and_range_proxy_stays_intact():
    server=(ROOT/'albert/server.py').read_text()
    assert "if path=='/api/media/ticket': return self._media_ticket_request(urlparse(self.path))" in server
    assert "if not self._require_endpoint('lo.use')" in server
    assert 'if handler.headers.get("Range")' in server
    assert 'req.add_header("Range",handler.headers.get("Range"))' in server
    assert "not _media_ticket_valid(ticket,node,item_id) and not self._require_endpoint('lo.use')" in server
