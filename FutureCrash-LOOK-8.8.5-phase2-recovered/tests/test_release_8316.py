from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_media_fabric_cli_get_has_catalog_specific_timeout():
    text=(ROOT / "core/node.py").read_text()
    assert "def _daemon_get(host: str, port: int, path: str, timeout=2.5):" in text
    assert '_daemon_get(a.host, a.port, "/v1/media/fabric", timeout=45.0)' in text

def test_ordinary_daemon_health_timeout_stays_short():
    text=(ROOT / "core/node.py").read_text()
    assert "timeout=2.5" in text
