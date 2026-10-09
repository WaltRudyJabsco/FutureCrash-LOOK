from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[1]

def test_850_component_versions_are_explicit():
    assert (ROOT/'VERSION').read_text().strip()=='8.10.2'
    assert (ROOT/'look/VERSION').read_text().strip()=='4.57.2'
    assert (ROOT/'future-crash/VERSION').read_text().strip()=='1.2.4'
    assert (ROOT/'albert/VERSION').read_text().strip()=='8.10.2'
    assert 'VERSION="4.57.2"' in (ROOT/'look/lk').read_text()
    assert 'LOOK_VERSION="4.57.2"' in (ROOT/'install-look.sh').read_text()

def test_850_player_shares_media_find_renderer():
    lk=(ROOT/'look/lk').read_text()
    block=lk[lk.index('def _media_player_render('):lk.index('def media_player(')]
    assert '_media_cover_lines(entry,art_w,11,background_remote=True)' in block
    assert '_media_player_art_lines(entry' not in block
    assert '_ansi_clip(art[i] if i<len(art) else "",art_w)' in block

def test_850_docs_name_current_release():
    assert (ROOT/'README.md').read_text().startswith('# Future Crash + LOOK 8.10.2 — FABRIC MEDIA')
    man=(ROOT/'look/lk.1').read_text()
    assert 'LOOK 4.57.2 / Future Crash + LOOK 8.10.2' in man
    assert 'Shift-R' in man and 'Shift-D' in man
