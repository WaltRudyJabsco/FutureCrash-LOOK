import importlib.util
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('configure_kitty',ROOT/'tools/configure_kitty.py')
setup=importlib.util.module_from_spec(spec);spec.loader.exec_module(setup)


def test_activation_preserves_previous_and_personal_overrides(tmp_path):
    source=ROOT/'terminal/kitty.conf'
    directory=tmp_path/'kitty';directory.mkdir()
    (directory/'kitty.conf').write_text('old profile')
    (directory/'kitty-local.conf').write_text('font_size 16')
    setup.configure(directory,source)
    assert (directory/'kitty.conf').read_bytes()==source.read_bytes()
    backups=list(directory.glob('kitty.conf.before-look-*'))
    assert len(backups)==1 and backups[0].read_text()=='old profile'
    assert (directory/'kitty-local.conf').read_text()=='font_size 16'
    setup.configure(directory,source)
    assert len(list(directory.glob('kitty.conf.before-look-*')))==1


def test_dry_run_does_not_create_files_and_symlink_target_is_untouched(tmp_path):
    directory=tmp_path/'kitty'
    source=ROOT/'terminal/kitty.conf'
    setup.configure(directory,source,dry_run=True)
    assert not directory.exists()
    directory.mkdir();target=tmp_path/'original';target.write_text('personal')
    (directory/'kitty.conf').symlink_to(target)
    setup.configure(directory,source)
    assert target.read_text()=='personal'
    backup=next(directory.glob('kitty.conf.before-look-*'))
    assert backup.is_symlink() and backup.resolve()==target
    assert not (directory/'kitty.conf').is_symlink()


def test_application_navigation_keys_are_not_terminal_shortcuts():
    text=(ROOT/'terminal/kitty.conf').read_text()
    bindings=[line.split()[1] for line in text.splitlines() if line.startswith('map ')]
    assert 'clear_all_shortcuts yes' in text
    assert not {'shift+up','shift+down','shift+left','shift+right','ctrl+r','alt+j','alt+k'}.intersection(bindings)
    assert 'ctrl+shift+page_up' in bindings
