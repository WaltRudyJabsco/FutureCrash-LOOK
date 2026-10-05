from pathlib import Path
import importlib.util
import sys

ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location('look_renderer_693',ROOT/'look'/'look_renderer.py')
mod=importlib.util.module_from_spec(SPEC); sys.modules[SPEC.name]=mod; SPEC.loader.exec_module(mod)


def test_meta_shift_hjkl_are_only_aliases_for_existing_arrows():
    assert mod.normalize_navigation_key('\x1bH') == '\x1b[D'
    assert mod.normalize_navigation_key('\x1bJ') == '\x1b[B'
    assert mod.normalize_navigation_key('\x1bK') == '\x1b[A'
    assert mod.normalize_navigation_key('\x1bL') == '\x1b[C'


def test_meta_shift_arrows_are_accelerated_navigation():
    assert mod.normalize_navigation_key('\x1b[1;4A') == 'pageup'
    assert mod.normalize_navigation_key('\x1b[1;4B') == 'pagedown'
    assert mod.normalize_navigation_key('\x1b[1;4D') == 'top'
    assert mod.normalize_navigation_key('\x1b[1;4C') == 'bottom'


def test_ordinary_keys_and_plain_arrows_are_unchanged():
    for key in ('g','G','h','H','\x1b[A','\x1b[B','\x1b[C','\x1b[D','\x1b[5~','\x1b[6~'):
        assert mod.normalize_navigation_key(key) == key


def test_g_contract_is_context_safe():
    source=(ROOT/'look'/'look_renderer.py').read_text()
    assert "elif key=='g': top=max(0,len(current)-usable) if top==0 else 0" in source
    assert "if key=='G' and on_go:" in source
    assert "if key in {'g','G'} and on_go:" not in source
    assert "'g ends','G go'" in source
