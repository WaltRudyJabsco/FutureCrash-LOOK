from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]

def test_release_versions_are_lockstep():
    assert (ROOT / "VERSION").read_text().strip() == "8.10.1"
    for rel in ("albert/VERSION",):
        assert (ROOT / rel).read_text().strip() == "8.10.1"
    for rel in ("core/node.py", "core/ingress.py", "core/tailcat.py", "core/rendezvous.py"):
        text = (ROOT / rel).read_text()
        release=(ROOT/'VERSION').read_text().strip()
        assert re.search(r'^VERSION = "'+re.escape(release)+r'"$', text, re.M)

def test_look_version_matches_installer_and_reports_product_release():
    lk = (ROOT / "look/lk").read_text()
    installer = (ROOT / "install-look.sh").read_text()
    lk_version = re.search(r'^VERSION="([^"]+)"$', lk, re.M).group(1)
    declared = re.search(r'^LOOK_VERSION="([^"]+)"$', installer, re.M).group(1)
    assert lk_version == declared == "4.57.1"
    assert 'Future Crash + LOOK {product_release}' in lk

def test_unified_installer_verifies_live_and_cli_versions():
    text = (ROOT / "install.sh").read_text()
    assert 'live Unified Node version' in text
    assert 'INSTALLED_LOOK_VERSION=' in text
    assert 'expected: LOOK $LOOK_SOURCE_VERSION · Future Crash + LOOK $EXPECTED_RELEASE' in text
    assert 'launchctl kickstart -k "gui/$(id -u)/com.futurecrash.look.node"' in text
