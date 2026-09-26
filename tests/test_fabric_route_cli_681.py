from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def test_lk_fabric_route_is_registered():
    text=(ROOT/"look/lk").read_text()
    assert '"route"' in text[text.index('if sub not in {'):text.index('argv=[exe,sub]')]
    assert 'route reflex|balanced|deep' in text

def test_node_route_uses_production_explainer():
    text=(ROOT/"core/node.py").read_text()
    assert 'from fabric_client import explain_route' in text or 'from .fabric_client import explain_route' in text
    assert 'explain_route(tier=tier' in text
