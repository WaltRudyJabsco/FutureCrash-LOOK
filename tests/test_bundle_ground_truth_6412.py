from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def test_bundle_versions_and_installer_identity_guard():
    assert (ROOT/'VERSION').read_text().strip()=='8.15.0'
    for rel in ('albert/VERSION',):
        assert (ROOT/rel).read_text().strip()=='8.15.0'
    install=(ROOT/'install.sh').read_text()
    assert 'BUNDLE SOURCE  $ROOT' in install
    assert 'BUNDLE RELEASE $EXPECTED_RELEASE · FABRIC VISION' in install
    assert 'core/node.py' in install and 'core/ingress.py' in install and 'core/tailcat.py' in install
    assert 'expected release 8.15.0' in install

def test_no_stale_fabric_user_agent():
    lk=(ROOT/'look/lk').read_text()
    assert 'Future-Crash-Fabric/8.15.0' in lk
    assert 'Future-Crash-Fabric/6.4.10' not in lk
    assert 'Future-Crash-Fabric/6.4.11' not in lk


def test_core_installation_copies_every_registered_python_module(tmp_path):
    import os,re,subprocess
    home=tmp_path/'home'
    (home/'.local/share/future-crash-look/core').mkdir(parents=True)
    lines=[line for line in (ROOT/'install.sh').read_text().splitlines()
           if re.match(r'install -m \d+ "\$ROOT/core/[^\"]+\.py" ',line)]
    env=dict(os.environ,ROOT=str(ROOT),HOME=str(home))
    subprocess.run(['bash','-e','-c','\n'.join(lines)],env=env,check=True)
    for source in (ROOT/'core').glob('*.py'):
        installed=home/'.local/share/future-crash-look/core'/source.name
        assert installed.read_bytes()==source.read_bytes(),source.name
