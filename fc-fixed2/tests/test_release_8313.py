from pathlib import Path
from unittest import mock

from core import tailcat

ROOT = Path(__file__).resolve().parents[1]


def test_mdns_hostname_never_doubles_local():
    with mock.patch("core.tailcat.socket.gethostname", return_value="Sashas-MacBook-Air.local"):
        assert tailcat._mdns_hostname() == "Sashas-MacBook-Air.local"
    with mock.patch("core.tailcat.socket.gethostname", return_value="Sashas-MacBook-Air.local.local."):
        assert tailcat._mdns_hostname() == "Sashas-MacBook-Air.local"


def test_launchd_tailscale_paths_are_explicit():
    src=(ROOT/"core/tailcat.py").read_text()
    assert "/opt/homebrew/bin/tailscale" in src
    assert "/Applications/Tailscale.app/Contents/MacOS/Tailscale" in src
    assert '"tailscale": tailscale' in src


def test_doctor_surfaces_tailcat_and_tailscale_state():
    src=(ROOT/"look/lk").read_text()
    assert "Tailcat {ad_version}" in src
    assert "Tailscale route" in src


def test_installer_verifies_live_tailcat_advertisement():
    src=(ROOT/"install.sh").read_text()
    assert "live Tailcat :7443 / advertisement" in src
    assert 'assert str(ad.get("version") or "") == expected' in src
    assert '.local.local:' in src
