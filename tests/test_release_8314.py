from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_release_and_serve_owner_contract():
    assert (ROOT / "VERSION").read_text().strip() == "8.16.0"
    install = (ROOT / "install.sh").read_text()
    assert 'core/tailscale_serve.py' in install
    assert 'tailscale serve --bg --https=7332' not in install
    helper = (ROOT / "core/tailscale_serve.py").read_text()
    assert '"--yes"' in helper
    assert '"serve", "reset"' not in helper
    for port in (7330, 7331, 7332):
        assert str(port) in helper


def test_look_product_version_bumped():
    lk = (ROOT / "look/lk").read_text()
    assert 'VERSION="4.63.0"' in lk
    assert 'Future-Crash-Fabric/8.16.0' in lk
