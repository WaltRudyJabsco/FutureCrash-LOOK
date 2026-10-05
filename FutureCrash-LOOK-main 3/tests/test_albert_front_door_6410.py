from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_albert_prefers_installed_fabric_core():
    text = (ROOT / 'albert' / 'server.py').read_text()
    assert 'Path.home()/".local/share/future-crash-look/core"' in text
    assert 'if not (CORE_DIR/"endpoint_auth.py").exists()' in text
    assert 'CORE_DIR=ROOT.parent/"core"' in text


def test_albert_health_is_a_hard_install_contract():
    child = (ROOT / 'albert' / 'install.sh').read_text()
    parent = (ROOT / 'install.sh').read_text()
    assert "Albert install failed:" in child
    assert "exit 1" in child
    assert '"$ROOT/albert/install.sh" || true' not in parent
    assert '"$ROOT/albert/install.sh"' in parent
