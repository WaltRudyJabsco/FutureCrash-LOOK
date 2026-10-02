from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_installer_trusts_service_manager_not_port_probe():
    text=(ROOT/'install.sh').read_text()
    assert 's.connect(("127.0.0.1",7332))' not in text
    assert 's.bind(("127.0.0.1",7332))' not in text
    assert 'still answering after stopping' not in text

def test_installer_restores_any_node_it_retires_on_failure():
    text=(ROOT/'install.sh').read_text()
    assert 'MANAGED_NODE_RETIRED=1' in text
    assert 'NODE_WAS_RUNNING' not in text
    assert 'NODE_STOPPED_BY_INSTALLER' not in text
    assert 'systemctl --user start future-crash-look-node.service' in text
    assert 'launchctl bootstrap "gui/$(id -u)" "$HOME/Library/LaunchAgents/com.futurecrash.look.node.plist"' in text
    assert 'launchctl kickstart -k "gui/$(id -u)/com.futurecrash.look.node"' in text
