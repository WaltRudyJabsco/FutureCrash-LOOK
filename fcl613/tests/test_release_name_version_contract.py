from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_installer_uses_machine_version_interface():
    text = (ROOT / "install.sh").read_text()
    assert "--version-number" in text
    assert "awk '{print $NF}'" not in text

def test_node_exposes_human_and_machine_versions():
    text = (ROOT / "core" / "node.py").read_text()
    assert 'RELEASE_NAME = "Safe Harbor"' in text
    assert '"--version-number"' in text
    assert 'version=VERSION' in text
