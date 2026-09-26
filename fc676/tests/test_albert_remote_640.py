from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def test_albert_stays_loopback_only():
    server=(ROOT/'albert/server.py').read_text()
    assert 'ALBERT_HOST","127.0.0.1"' in server

def test_installer_publishes_albert_over_tailscale_serve():
    installer=(ROOT/'install.sh').read_text()
    assert 'tailscale serve --bg --https=7330 "$ALBERT_BACKEND"' in installer
    assert 'ALBERT_BACKEND="http://127.0.0.1:7330"' in installer

def test_node_advertises_albert_urls():
    node=(ROOT/'core/node.py').read_text()
    assert 'def albert_urls()' in node
    assert 'https://{dns}:7330' in node
    assert '"albert.urls": albert_urls()' in node

def test_look_has_ipad_handoff_commands():
    lk=(ROOT/'look/lk').read_text()
    assert 'if sub in {"url","share"}' in lk
    assert 'if sub=="qr"' in lk
    assert 'if sub in {"remote","ipad"}' in lk


def test_albert_service_has_tool_path():
    unit=(ROOT/'albert/albert.service').read_text()
    install=(ROOT/'albert/install.sh').read_text()
    assert '.local/bin' in unit
    assert '/opt/homebrew/bin' in install
