from pathlib import Path
import importlib.machinery, importlib.util, shutil, sys

ROOT = Path(__file__).resolve().parents[1]


def _load_lk(name='look_lk_installed_704'):
    loader = importlib.machinery.SourceFileLoader(name, str(ROOT / 'look' / 'lk'))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[loader.name] = mod
    loader.exec_module(mod)
    return mod


def test_unified_installer_ships_and_verifies_jev():
    text = (ROOT / 'install.sh').read_text()
    assert 'install -m 0644 "$ROOT/core/jev.py" "$HOME/.local/share/future-crash-look/core/jev.py"' in text
    assert 'cmp -s "$ROOT/core/jev.py" "$HOME/.local/share/future-crash-look/core/jev.py"' in text
    assert 'import fabric_identity, endpoint_auth, intent_normalizer, tailcat, rendezvous' in text
    assert 'import jev' in text
    assert 'callable(jev.command_imperative)' in text


def test_jev_loads_from_installed_layout_without_source_tree(tmp_path, monkeypatch):
    home = tmp_path / 'home'
    installed_core = home / '.local/share/future-crash-look/core'
    installed_core.mkdir(parents=True)
    shutil.copy2(ROOT / 'core' / 'jev.py', installed_core / 'jev.py')

    lk = _load_lk()
    monkeypatch.setattr(lk.Path, 'home', classmethod(lambda cls: home))
    monkeypatch.setattr(lk, 'ROOT', home / '.local/share/look')
    # Remove any source-tree JEV that earlier tests may have imported.
    sys.modules.pop('jev', None)
    source_core = str(ROOT / 'core')
    while source_core in sys.path:
        sys.path.remove(source_core)

    loaded = lk._jev_module()
    assert Path(loaded.__file__).resolve() == (installed_core / 'jev.py').resolve()
    decision = loaded.command_imperative('run asciiquarium in new terminal', head_resolves=lambda _: False)
    assert decision['command'] == 'asciiquarium'
    assert decision['terminal'] == 'new'
