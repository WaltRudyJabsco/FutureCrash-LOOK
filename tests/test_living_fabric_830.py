from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def test_media_logical_view_and_visibility_controls_are_shipped():
    s=(ROOT/'look'/'lk').read_text()
    for token in ('def _media_collapse(', 'source_count', 'ALL SOURCES', 'hidden_trees', 'hidden_paths', 'V sources', 'H hidden', 'X hide', 'D hide tree'):
        assert token in s

def test_large_game_sprites_and_red_blue_vocabulary():
    s=(ROOT/'look'/'games.py').read_text()
    assert 'sprites={' in s and '██████' in s
    assert 'RED' in s and '"BLUE" if who=="W" else "RED"' in s

def test_mini_dash_has_clock_date_media_signal_and_two_recent_events():
    s=(ROOT/'core'/'node.py').read_text()
    assert 'FUTURE CRASH · {time.strftime' in s
    assert 'time.strftime("%a %b %d").upper()' in s
    assert '_dash_media_line()' in s and '_dash_signal(data' in s
    assert '_dash_recent_events(events,2)' in s
