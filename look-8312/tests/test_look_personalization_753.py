from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
LK=(ROOT/'look/lk').read_text()
RENDERER=(ROOT/'look/look_renderer.py').read_text()
NODE=(ROOT/'core/node.py').read_text()
ALBERT=(ROOT/'albert/index.html').read_text()
SIGNAL=(ROOT/'signal-window/app.js').read_text()


def test_navigation_contract_is_preserved_while_personalization_grows():
    assert "if key in {'\\x1b[B','j'} and matches:" in RENDERER
    assert 'if cursoring:' in RENDERER
    assert "Space/PgDn next" in RENDERER
    assert "Enter/→ filter" in RENDERER


def test_renderer_preferences_are_bounded_and_nerd_is_default():
    assert "data={'icons':'nerd','preview':'ascii'}" in RENDERER
    assert "--format=symbols" in RENDERER
    assert "def _terminal_graphics_format()" not in RENDERER
    assert "--format=kitty" not in RENDERER
    assert "--format=iterm" not in RENDERER
    assert "--format=sixels" not in RENDERER


def test_feedback_is_semantic_not_keypress_sound():
    assert 'data={"sound":"off","motion":"subtle"}' in LK
    assert 'sound=="expressive"' in LK
    assert 'sound=="subtle" and kind in {"complete","error","notify"}' in LK
    assert '_feedback("complete",f"{kind} complete")' in LK


def test_shared_voice_profiles_and_personality_override_switch():
    assert 'SPEECH_CONFIG_FILE=CONFIG_DIR/"speech.json"' in LK
    for name in ('albert','warm','crisp','deep','max','philosopher','pirate','wopr'):
        assert f'"{name}"' in LK or f"'{name}'" in NODE
    assert '"personality_voices":True' in LK
    assert 'def _resolve_voice_profile' in LK
    assert "profile=_resolve_voice_profile(voice_profile)" in NODE


def test_browser_speech_understands_named_profiles():
    assert 'function speechProfile(name)' in ALBERT
    assert 'function speechProfile(name)' in SIGNAL
    assert 'philosopher' in ALBERT and 'pirate' in ALBERT
