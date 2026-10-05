from pathlib import Path
import ast


def test_preview_never_reads_entire_file():
    src=Path('look/look_renderer.py').read_text()
    assert 'read_bytes()[:65536]' not in src
    assert "handle.read(65536)" in src
    assert 'S_ISREG' in src


def test_renderer_and_lk_swallow_keyboard_interrupt_traceback():
    for f in ('look/look_renderer.py','look/lk'):
        src=Path(f).read_text()
        assert 'except KeyboardInterrupt' in src
        ast.parse(src)


def test_removable_media_watcher_is_autostarted_on_both_platforms():
    install=Path('install.sh').read_text()
    assert 'future-crash-look-media-watch.service' in install
    assert 'systemctl --user enable future-crash-look-node.service future-crash-look-ingress.service future-crash-look-media-watch.service' in install
    assert 'com.futurecrash.look.media-watch.plist' in install
    plist=Path('core/com.futurecrash.look.media-watch.plist').read_text()
    assert '<key>RunAtLoad</key><true/>' in plist
    assert '<key>KeepAlive</key><true/>' in plist


def test_games_are_large_terminal_boards_and_gtnw_logic_not_rewritten():
    src=Path('look/games.py').read_text()
    assert 'sprites={' in src and '██████' in src
    assert '" ▄●▄  "' in src
    assert '─────────┼─────────┼─────────' in src
    assert 'if game=="gtnw"' in src and 'gtnw_runner' in src
