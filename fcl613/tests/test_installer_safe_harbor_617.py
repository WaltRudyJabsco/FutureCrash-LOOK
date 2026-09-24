from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_installer_checks_exact_local_endpoint_not_bind():
    text=(ROOT/'install.sh').read_text()
    assert 's.connect(("127.0.0.1",7332))' in text
    assert 's.bind(("127.0.0.1",7332))' not in text
    assert "grep -E '127\\.0\\.0\\.1:7332" in text

def test_installer_restores_running_node_on_failure():
    text=(ROOT/'install.sh').read_text()
    assert 'restore_node_on_failure' in text
    assert 'NODE_WAS_RUNNING' in text
    assert 'systemctl --user start future-crash-look-node.service' in text
