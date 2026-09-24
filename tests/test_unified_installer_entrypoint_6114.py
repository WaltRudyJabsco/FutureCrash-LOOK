from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_install_look_delegates_to_unified_installer():
    text = (ROOT / "install-look.sh").read_text()
    assert "FCL_UNIFIED_INSTALL_CHILD" in text
    assert 'exec "$ROOT/install.sh" "$@"' in text

def test_unified_installer_marks_look_phase_as_child():
    text = (ROOT / "install.sh").read_text()
    assert 'FCL_UNIFIED_INSTALL_CHILD=1 "$ROOT/install-look.sh" "$@"' in text

def test_install_look_reads_bundle_version():
    text = (ROOT / "install-look.sh").read_text()
    assert 'PRODUCT_VERSION="$(tr -d' in text
    assert '6.1.12' not in text


def test_installer_carries_shared_intent_normalizer():
    root=Path(__file__).resolve().parents[1]
    text=(root/'install.sh').read_text()
    assert 'core/intent_normalizer.py' in text
    assert 'import fabric_identity, endpoint_auth, intent_normalizer, tailcat' in text
