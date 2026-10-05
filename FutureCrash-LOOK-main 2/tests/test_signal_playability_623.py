from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/'signal-window/app.js').read_text()


def test_browser_rejects_explicit_protected_media_before_play():
    assert "hint==='protected_or_restricted'" in APP
    assert 'choose another item or a native output' in APP


def test_runtime_decode_and_unsupported_errors_offer_cheap_fallback():
    assert "code===3?'decode'" in APP
    assert "code===4?'unsupported source/codec'" in APP
    assert "try another item or a native output" in APP
