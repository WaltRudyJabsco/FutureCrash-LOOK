from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
INSTALL=(ROOT/'install.sh').read_text()
LOOK_INSTALL=(ROOT/'install-look.sh').read_text()
RENDERER=(ROOT/'look'/'look_renderer.py').read_text()

def test_macos_node_bootstrap_is_followed_by_kickstart():
    assert 'launchctl bootstrap "gui/$(id -u)" "$HOME/Library/LaunchAgents/com.futurecrash.look.node.plist"' in INSTALL
    assert 'launchctl kickstart -k "gui/$(id -u)/com.futurecrash.look.node"' in INSTALL

def test_node_failure_diagnostics_are_platform_specific():
    assert 'launchd state:' in INSTALL
    assert 'systemd state:' in INSTALL
    assert '$HOME/.local/share/future-crash-look/node.log' in INSTALL

def test_kitty_helpers_are_checked_independently():
    assert 'NEED_KITTY=0; NEED_IMAGE=0; NEED_PDF=0' in LOOK_INSTALL
    assert 'command -v pdftoppm' in LOOK_INSTALL
    assert 'command -v magick' in LOOK_INSTALL

def test_kitty_png_has_direct_fallback_and_does_not_move_cursor():
    assert "self.driver=='kitty' and path.suffix.casefold()=='.png'" in RENDERER
    assert 'C=1,q=2' in RENDERER

def test_prompt_capitalization_matches_default_semantics():
    assert '"$prompt [Y/n] "' in LOOK_INSTALL
    assert '"$prompt [y/N] "' in LOOK_INSTALL
