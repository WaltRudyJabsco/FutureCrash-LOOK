from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / 'look' / 'lk').read_text()


def test_media_filter_does_not_steal_lowercase_j_k():
    block = SOURCE[SOURCE.index('def _media_selector('):SOURCE.index('def _media_selector_finish(')]
    assert 'if key in {"up","K"} and visible:' in block
    assert 'if key in {"down","J"} and visible:' in block
    assert 'if key in {"up","k"} and visible:' not in block
    assert 'if key in {"down","j"} and visible:' not in block
    assert 'if len(key)==1 and key.isprintable()' in block


def test_shared_selector_only_uses_lowercase_j_k_outside_filter_mode():
    start = SOURCE.index('def _select_values(')
    end = SOURCE.index('\n\ndef inspect_up', start)
    block = SOURCE[start:end]
    assert '(key=="k" and not filtering)' in block
    assert '(key=="j" and not filtering)' in block
    assert 'if filtering and len(key)==1 and key.isprintable()' in block
