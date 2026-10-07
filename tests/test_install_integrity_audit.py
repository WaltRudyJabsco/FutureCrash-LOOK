from pathlib import Path
import importlib.util
import sys

ROOT=Path(__file__).resolve().parents[1]


def test_look_installer_verifies_each_runtime_copy_immediately():
    source=(ROOT/'install-look.sh').read_text()
    helper=source[source.index('install_file() {'):source.index('\nask() {')]
    assert 'cmp -s "$src" "$dst"' in helper
    assert 'exit 5' in helper
    assert 'install_file "$ROOT/look/look_renderer.py" "$HOME/.local/share/look/look_renderer.py"' in source
    for name in ('lk','look_ai.py','lo_engine.py','lo_stream.py','media_core.py','media_art.py','media_watch.py','file_catalog.py','games.py','comfy_bootstrap.py'):
        assert f'install_file "$ROOT/look/{name}"' in source


def test_unified_installer_rechecks_renderer_at_release_boundary():
    source=(ROOT/'install.sh').read_text()
    assert 'verify_same "$ROOT/look/look_renderer.py" "$HOME/.local/share/look/look_renderer.py" "LOOK renderer"' in source
    assert 'verify_same "$ROOT/look/lo_stream.py" "$HOME/.local/share/look/lo_stream.py" "LO stream assembler"' in source


def test_code_health_invariants_are_machine_checkable():
    path=ROOT/'tools/code_health.py'
    spec=importlib.util.spec_from_file_location('code_health_audit',path)
    module=importlib.util.module_from_spec(spec); sys.modules[spec.name]=module; spec.loader.exec_module(module)
    report=module.analyze()
    assert report['parse_errors']==[]
    assert report['duplicate_definitions']==[]
    assert report['legacy_pager_states']==[]
