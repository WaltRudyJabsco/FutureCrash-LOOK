from pathlib import Path
import importlib.util
import types

ROOT=Path(__file__).resolve().parents[1]
NODE=(ROOT/'core/node.py').read_text()
LK=(ROOT/'look/lk').read_text()


def test_owner_exposes_source_local_terminal_preview_route():
    assert 'def _local_media_terminal_preview(entry_id, path_hint="", width=22, height=11):' in NODE
    assert '[chafa,"--format=symbols","--colors","full","--color-space","rgb","--size",f"{width}x{height}",str(art)]' in NODE
    assert 'def _serve_media_terminal_preview(self,target,entry_id,path_hint="",width=22,height=11):' in NODE
    assert 'base+"/v1/preview/terminal?"' in NODE
    get_block=NODE[NODE.index('    def do_GET(self):'):]
    assert 'if path == "/v1/preview/terminal":' in get_block


def test_player_prefers_memory_only_remote_terminal_rows():
    assert '_REMOTE_MEDIA_PREVIEW_CACHE={}' in LK
    assert 'while len(_REMOTE_MEDIA_PREVIEW_CACHE)>64:' in LK
    preview=LK[LK.index('def _media_fetch_remote_preview'):LK.index('def _media_remote_cover_path')]
    assert "7332/v1/preview/terminal?" in preview
    assert '_REMOTE_MEDIA_PREVIEW_LATEST' in preview
    assert '_media_remote_preview_worker_loop' in preview
    assert "write_bytes" not in preview
    cover=LK[LK.index('def _media_cover_lines'):LK.index('def _media_player_art_lines')]
    assert '_media_remote_preview_lines(row,width,height,background=background_remote)' in cover
    assert '_media_remote_cover_path(row)' in cover  # older peers still work


def test_player_timestamp_is_left_anchored_and_bar_is_disposable_width():
    block=LK[LK.index('def _media_player_render'):LK.index('def media_player')]
    assert 'time_text=f"{_media_time(pos)} / {_media_time(duration)}"' in block
    assert 'bar_width=max(4,inner-len(time_text)-2)' in block
    assert 'f"{time_text}  {bar}"' in block
    assert 'f"{bar}  {_media_time(pos)} / {_media_time(duration)}"' not in block
    assert 'ART… loading remote preview' in block
