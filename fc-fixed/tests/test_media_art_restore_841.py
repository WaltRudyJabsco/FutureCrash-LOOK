from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
LK=(ROOT/'look/lk').read_text()

def _block(name,next_name):
    start=LK.index(f'def {name}')
    end=LK.index(f'def {next_name}',start)
    return LK[start:end]

def test_media_find_restores_8318_direct_path_first():
    block=_block('_media_cover_lines','_media_player_art_lines')
    direct='media_art.symbol_lines(direct,width,height)'
    fallback='_media_art_source(row)'
    assert direct in block and fallback in block
    assert block.index(direct) < block.index(fallback)

def test_player_uses_same_direct_art_source_first():
    block=_block('_media_player_art_lines','_media_detail_lines')
    direct='media_art.ascii_lines(direct,width,height)'
    fallback='_media_art_source(row)'
    assert direct in block and fallback in block
    assert block.index(direct) < block.index(fallback)
    assert 'media_art.ascii_lines(direct,width,height)' in block
