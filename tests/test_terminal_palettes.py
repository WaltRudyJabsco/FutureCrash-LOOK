from pathlib import Path
from unittest.mock import Mock

import pytest
from look import terminal_style as styles

ROOT=Path(__file__).resolve().parents[1]


def test_switching_and_reset_keep_existing_neon_opacity_keys_and_font(tmp_path):
    folder=tmp_path/'kitty';folder.mkdir()
    before=(ROOT/'terminal/kitty.conf').read_text().replace('background_opacity 0.82','background_opacity 0.72')
    before=before.replace(styles.INCLUDE+'\n','')
    (folder/'kitty.conf').write_text(before)
    (folder/'kitty-local.conf').write_text('font_size 15\n')
    styles.select_theme('paper',folder)
    config=(folder/'kitty.conf').read_text()
    assert config.replace(styles.INCLUDE+'\n','')==before
    assert config.index(styles.INCLUDE)<config.index(styles.PERSONAL)
    assert (folder/'look-theme.conf').read_text().startswith('# LOOK palette: paper')
    assert 'background_opacity 1.0' in (folder/'look-theme.conf').read_text()
    styles.select_theme('paper',folder)
    assert not list(folder.glob('look-theme.conf.before-*'))
    styles.select_theme('neon',folder)
    assert 'background_opacity' not in (folder/'look-theme.conf').read_text()
    styles.select_theme('reset',folder)
    assert (folder/'look-theme.conf').read_text()=='# LOOK palette: reset\n'
    assert (folder/'kitty-local.conf').read_text()=='font_size 15\n'
    assert len(list(folder.glob('kitty.conf.before-look-theme-*')))==1


def test_theme_config_symlink_is_backed_up_without_editing_target(tmp_path):
    original=tmp_path/'personal.conf';original.write_text('font_size 17\n')
    folder=tmp_path/'kitty';folder.mkdir();(folder/'kitty.conf').symlink_to(original)
    styles.select_theme('paper',folder)
    assert original.read_text()=='font_size 17\n'
    assert next(folder.glob('kitty.conf.before-look-theme-*')).is_symlink()
    with pytest.raises(ValueError):styles.select_theme('unknown',folder)


def test_launch_applies_only_new_window_overrides(monkeypatch,tmp_path):
    monkeypatch.setattr(styles,'kitty_executable',lambda:'/kitten/kitty')
    launch=Mock();monkeypatch.setattr(styles.subprocess,'Popen',launch)
    monkeypatch.setenv('KITTY_CONFIG_DIRECTORY',str(tmp_path))
    assert styles.main(['launch','paper'])==0
    args=launch.call_args.args[0]
    assert args[0]=='/kitten/kitty' and 'background=#f6f1e7' in args
    assert 'foreground=#201e1a' in args and 'background_opacity=1.0' in args
    assert not list(tmp_path.iterdir())


def test_missing_config_cannot_be_overwritten_and_readonly_listing_creates_nothing(tmp_path,monkeypatch):
    monkeypatch.setenv('KITTY_CONFIG_DIRECTORY',str(tmp_path/'kitty'))
    assert styles.main([])==0
    assert not (tmp_path/'kitty').exists()
    assert styles.main(['theme','paper'])==1
    assert not (tmp_path/'kitty').exists()


def test_reload_checks_process_before_sending_signal(monkeypatch):
    monkeypatch.setenv('KITTY_PID','123')
    monkeypatch.setattr(styles.subprocess,'run',Mock(return_value=Mock(stdout='/usr/bin/zsh\n')))
    send=Mock();monkeypatch.setattr(styles.os,'kill',send)
    assert not styles.reload_kitty();send.assert_not_called()
    monkeypatch.setattr(styles.subprocess,'run',Mock(return_value=Mock(stdout='/Applications/kitty.app/Contents/MacOS/kitty\n')))
    assert styles.reload_kitty()
    send.assert_called_once_with(123,styles.signal.SIGUSR1)


def test_paper_palette_has_readable_notes_and_album_accents():
    theme=styles.settings('paper')
    def linear(value):
        number=int(value,16)/255
        return number/12.92 if number<=.04045 else ((number+.055)/1.055)**2.4
    def luminance(color):
        return sum(weight*linear(color[index:index+2]) for index,weight in ((1,.2126),(3,.7152),(5,.0722)))
    background=luminance(theme['background'])
    for key in ('foreground','color81','color117','color150','color180','color183','color110','color211'):
        ink=luminance(theme[key])
        assert (background+.05)/(ink+.05)>=4.5


@pytest.mark.parametrize('theme',['paper','custom','slate','neon'])
def test_future_crash_uses_shared_inks_and_retains_dark_theme_palette(monkeypatch,theme,tmp_path):
    import importlib.util
    monkeypatch.setenv('LOOK_TERMINAL_THEME',theme)
    monkeypatch.setenv('KITTY_CONFIG_DIRECTORY',str(tmp_path))
    spec=importlib.util.spec_from_file_location('fc_ink_test',ROOT/'future-crash/future_crash.py')
    module=importlib.util.module_from_spec(spec)
    import sys
    monkeypatch.setitem(sys.modules,spec.name,module);spec.loader.exec_module(module)
    if theme in {'paper','custom'}:
        assert module.WHITE=='\x1b[38;2;32;30;26m'
        assert module.GREEN.startswith('\x1b[38;2;')
        assert module.GREEN2==module.GREEN
        assert module.SignalCanvas.COLORS['green']==module.GREEN
    else:
        assert module.GREEN=='\x1b[38;5;121m'
        assert module.WHITE=='\x1b[38;5;255m'


def test_future_crash_standalone_needs_no_shared_theme_helper(tmp_path,monkeypatch):
    import importlib.util,sys
    path=tmp_path/'future_crash.py'
    path.write_text((ROOT/'future-crash/future_crash.py').read_text())
    monkeypatch.setenv('LOOK_TERMINAL_THEME','paper')
    spec=importlib.util.spec_from_file_location('fc_standalone_ink_test',path)
    module=importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules,spec.name,module);spec.loader.exec_module(module)
    assert module.GREEN=='\x1b[38;5;121m'
    assert module.application_palette()=={}
