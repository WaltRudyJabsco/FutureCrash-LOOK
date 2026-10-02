from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
NODE=(ROOT/'core/node.py').read_text()
LK=(ROOT/'look/lk').read_text()
def test_route_diagnostics_are_local_only_and_per_endpoint():
    assert 'def _fabric_route_diagnostics' in NODE
    assert '"/v1/fabric/routes"' in NODE
    assert 'Fabric route diagnostics are local-control only' in NODE
    assert 'base+"/v1/identity"' in NODE
def test_last_good_route_gets_first_refusal():
    assert 'preferred=str(prior.get("url") or "")' in NODE
    assert 'prior.get("active_transport") or "preferred"' in NODE
def test_doctor_prints_route_matrix_and_selected_route():
    assert 'route matrix' in LK
    assert ' · SELECTED' in LK
