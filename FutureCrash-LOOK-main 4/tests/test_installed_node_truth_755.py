import os
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_installer_ships_attention_module():
    text = (ROOT / "install.sh").read_text()
    assert 'core/attention.py' in text


def test_installed_fcl_node_reports_release_from_clean_home(tmp_path):
    """The release is valid only if the files install.sh ships can boot fcl-node."""
    install = (ROOT / "install.sh").read_text()
    home = tmp_path / "home"
    core = home / ".local/share/future-crash-look/core"
    bindir = home / ".local/bin"
    core.mkdir(parents=True)
    bindir.mkdir(parents=True)

    pattern = re.compile(r'install -m \d+ "\$ROOT/core/([^\"]+)" "\$HOME/\.local/(?:share/future-crash-look/core|bin)/([^\"]+)"')
    shipped = pattern.findall(install)
    assert shipped
    for source_name, dest_name in shipped:
        source = ROOT / "core" / source_name
        dest = bindir / dest_name if dest_name.startswith("fcl-") else core / dest_name
        shutil.copy2(source, dest)
        if os.access(source, os.X_OK):
            dest.chmod(dest.stat().st_mode | 0o111)

    result = subprocess.run(
        [str(bindir / "fcl-node"), "--version-number"],
        env={**os.environ, "HOME": str(home)},
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == (ROOT / "VERSION").read_text().strip()
