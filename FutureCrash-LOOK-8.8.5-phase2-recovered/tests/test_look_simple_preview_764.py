from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
RENDERER=(ROOT/"look/look_renderer.py").read_text()
LK=(ROOT/"look/lk").read_text()

def test_preview_is_composed_symbol_rows_only():
    assert "--format=symbols" in RENDERER
    assert "def _terminal_graphics_format" not in RENDERER
    for protocol in ("--format=kitty","--format=iterm","--format=sixels"):
        assert protocol not in RENDERER

def test_preview_has_no_async_pager_machinery():
    for token in ("preview_deadline","preview_generation","preview_worker","_clear_native_preview","_native_preview_block"):
        assert token not in RENDERER

def test_preview_settings_are_ascii_or_off():
    block=LK[LK.index("def _settings_pick_preview"):LK.index("def _settings_set_preview")]
    assert '("ascii"' in block and '("off"' in block
    assert '("graphics"' not in block and '("auto"' not in block
