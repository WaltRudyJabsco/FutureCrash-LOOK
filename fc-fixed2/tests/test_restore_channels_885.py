from pathlib import Path
import importlib.util
ROOT=Path(__file__).resolve().parents[1]

def load_intents():
    spec=importlib.util.spec_from_file_location("intent_normalizer", ROOT/"core/intent_normalizer.py")
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod

def test_signal_named_stations_precede_generic_media():
    s=(ROOT/"signal-window/server.py").read_text()
    generic=s.index('intent_resolution=resolve_intent(prompt)')
    for phrase in ('play classical','play classics','play arts','play arts channel'):
        assert phrase in s[:generic]
    assert 'All Classical Radio' in s[:generic]
    assert 'Classic Arts Showcase' in s[:generic]

def test_signal_browser_accepts_direct_builtin_stream_url():
    s=(ROOT/"signal-window/app.js").read_text()
    assert "entry?.url||entry?.stream_url" in s

def test_albert_keeps_arts_channel_alias():
    s=(ROOT/"albert/server.py").read_text()
    assert '"play arts channel"' in s

def test_autoplay_respects_hidden_and_micro_samples():
    s=(ROOT/"look/lk").read_text()
    assert 'def _media_autoplay_eligible(row):' in s
    assert 'if _media_is_hidden(row): return False' in s
    assert '0 < duration < 3.0' in s
    assert 'rows=[row for row in rows if _media_autoplay_eligible(row)]' in s

def test_real_lk_compiles():
    import py_compile
    py_compile.compile(str(ROOT/"look/lk"), doraise=True)
