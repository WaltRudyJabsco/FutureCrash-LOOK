from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def test_albert_video_choices_are_strict_and_conversational():
    s=(ROOT/'albert/server.py').read_text()
    assert 'choose_random={"r","random","surprise me","you choose"' in s
    assert "suffix.casefold() not in exts" in s
    assert "startswith('video/') or Path" not in s[s.index('def _broad_video_choices'):s.index('def action')]
    assert 'Do not leak a plausible reply to general cognition' in s

def test_signal_video_choices_are_strict_and_conversational():
    s=(ROOT/'signal-window/server.py').read_text()
    block=s[s.index('def _video_row'):s.index('def _video_label')]
    assert 'return ext in {' in block
    assert 'mt.startswith("video/")' not in block
    assert '"you choose"' in s[s.index('def _signal_pending_media'):s.index('def _signal_choice_text')]
    assert '"reprompt":True' in s
