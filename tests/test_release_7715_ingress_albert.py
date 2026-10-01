from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def test_installer_retries_ingress_metrics_before_rollback():
    text=(ROOT/'install.sh').read_text()
    assert 'INGRESS_READY=0' in text
    assert 'for _ in {1..40}; do' in text
    assert 'http://127.0.0.1:7333/_fcl/metrics' in text
    assert 'if (( ! INGRESS_READY )); then' in text

def test_albert_supports_browser_head_probe_for_ticketed_media():
    text=(ROOT/'albert/server.py').read_text()
    start=text.index('    def do_HEAD(self):')
    end=text.index('    def do_GET(self):',start)
    block=text[start:end]
    assert "if path=='/v1/media/item':" in block
    assert '_media_ticket_valid(ticket,node,item_id)' in block
    assert '_proxy_media_item(self,node,item_id,head=True)' in block
