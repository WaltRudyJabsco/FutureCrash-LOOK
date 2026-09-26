from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def test_bundle_versions_and_installer_identity_guard():
    assert (ROOT/'VERSION').read_text().strip()=='6.7.6'
    for rel in ('look/VERSION','albert/VERSION','future-crash/VERSION'):
        assert (ROOT/rel).read_text().strip()=='6.7.6'
    install=(ROOT/'install.sh').read_text()
    assert 'BUNDLE SOURCE  $ROOT' in install
    assert 'BUNDLE RELEASE $EXPECTED_RELEASE · CANONICAL EDGE' in install
    assert 'core/node.py' in install and 'core/ingress.py' in install and 'core/tailcat.py' in install
    assert 'expected release 6.7.6' in install

def test_no_stale_fabric_user_agent():
    lk=(ROOT/'look/lk').read_text()
    assert 'Future-Crash-Fabric/6.7.6' in lk
    assert 'Future-Crash-Fabric/6.4.10' not in lk
    assert 'Future-Crash-Fabric/6.4.11' not in lk
