from pathlib import Path

LK=Path('look/lk').read_text()
NODE=Path('core/node.py').read_text()
ART=Path('look/media_art.py').read_text()


def block(text,start,end):
    return text.split(start,1)[1].split(end,1)[0]


def test_media_find_frame_clears_each_row_without_blank_clear():
    fn=block(LK,'def _terminal_frame_payload(frame):','def _ansi_clip')
    assert 'row+"\\033[K"' in fn
    selector=block(LK,'def _media_selector(rows,title="FABRIC MEDIA",initial_query="",catalog_meta=None):','def _media_selector_finish')
    assert 'sys.stdout.write(_terminal_frame_payload(frame))' in selector
    assert 'sys.stdout.write("\\033[H"+frame+"\\033[J")' not in selector


def test_interactive_remote_art_is_nonblocking_latest_wins():
    worker=block(LK,'def _media_remote_preview_worker_loop():','def _media_remote_cover_path')
    assert '_REMOTE_MEDIA_PREVIEW_LATEST' in worker
    assert 'One worker prevents an arrow-key' in worker
    cover=block(LK,'def _media_cover_lines(row,width,height=11,background_remote=False):','def _media_player_art_lines')
    assert 'if background_remote:' in cover
    assert 'Interactive surfaces must never block navigation' in cover
    # Compatibility image fetch remains only after the nonblocking return.
    assert cover.index('if background_remote:') < cover.index('_media_remote_cover_path(row)')


def test_remote_and_local_chafa_are_explicit_full_rgb():
    local="[chafa,'--format=symbols','--colors','full','--color-space','rgb','--size',f'{width}x{height}',str(art)]"
    remote='[chafa,"--format=symbols","--colors","full","--color-space","rgb","--size",f"{width}x{height}",str(art)]'
    assert local in ART
    assert remote in NODE


def test_art_status_is_diagnostic_not_ambiguous():
    selector=block(LK,'def _media_selector(rows,title="FABRIC MEDIA",initial_query="",catalog_meta=None):','def _media_selector_finish')
    assert 'ART… requesting {art_owner}' in selector
    assert 'ART unavailable' in selector
    player=block(LK,'def _media_player_render():','def media_player():')
    assert 'ART… requesting {art_owner}' in player
    assert 'ART unavailable' in player
