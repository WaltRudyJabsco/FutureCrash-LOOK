from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
LK=(ROOT/'look'/'lk').read_text()
NODE=(ROOT/'core'/'node.py').read_text()
SIGNAL=(ROOT/'signal-window'/'server.py').read_text()


def test_direct_lk_play_normalizes_selectors_before_catalog_lookup():
    block=LK[LK.index('def _media_resolve_targets'):LK.index('def _media_prepare_command')]
    assert 'normalizer.resolve("play "+text)' in block
    assert 'intent.get("action")=="media.play"' in block
    assert 'media_core.select_entries' in block


def test_direct_cli_has_explicit_exact_escape_hatch():
    block=LK[LK.index('def _media_resolve_targets'):LK.index('def _media_prepare_command')]
    assert '{"--exact","--literal"}' in block
    assert 'match_mode="literal" if exact else "fuzzy"' in block


def test_literal_mode_survives_signal_and_node_route():
    assert '"shuffle","match_mode"' in SIGNAL
    assert 'match_mode = str(payload.get("match_mode")' in NODE
    assert 'if match_mode == "literal": argv.append("--exact")' in NODE

def test_completion_teaches_top_level_play_and_exact_mode():
    completion=(ROOT/'look'/'completions'/'_lk').read_text()
    assert "'play:play media with selector/fuzzy matching'" in completion
    assert "_values 'play option' --exact --literal --shuffle" in completion
