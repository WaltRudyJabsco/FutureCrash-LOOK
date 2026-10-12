from types import SimpleNamespace
from unittest.mock import Mock
import pytest
from test_future_crash_editor import MOD as fc


def test_negative_rows_preserve_glyphs_and_reset_before_surrounding_ui():
    app=fc.FutureCrash.__new__(fc.FutureCrash)
    row=fc.GREEN+'A'+fc.RESET+' '+fc.CYAN+'B'+fc.RESET
    app.signal_style='normal'
    assert app.render_signal_row(row)==row
    app.signal_style='negative';negative=app.render_signal_row(row)
    assert fc.strip_ansi(negative)==fc.strip_ansi(row)=='A B'
    assert negative.startswith(fc.CYAN+fc.CSI+'7m') and negative.endswith(fc.RESET)
    assert negative.count(fc.RESET)==1
    assert fc.GREEN not in negative


def test_toggle_saves_style_without_changing_drawing_or_audio():
    app=fc.FutureCrash.__new__(fc.FutureCrash)
    app.mode='ambient';app.signal_style='normal';app.config=SimpleNamespace(signal_style='normal')
    app.signal=Mock();app.audio=Mock();app.last_frame='old'
    app.handle_key('v')
    assert app.signal_style==app.config.signal_style=='negative' and app.last_frame==''
    app.handle_key('V');assert app.signal_style=='normal'
    app.signal.assert_not_called();assert not app.signal.method_calls
    assert not app.audio.method_calls


def test_style_preference_preserves_other_settings_and_rejects_invalid(tmp_path,monkeypatch):
    monkeypatch.setattr(fc.Path,'home',lambda:tmp_path)
    config=fc.ConfigStore();config.audio_enabled=False;config.data['other']='keep'
    config.signal_style='negative';loaded=fc.ConfigStore()
    assert loaded.signal_style=='negative' and not loaded.audio_enabled and loaded.data['other']=='keep'
    loaded.data['signal_style']='bad';assert loaded.signal_style=='normal'
    with pytest.raises(ValueError):loaded.signal_style='bad'


def test_conversation_panel_inverts_only_signal_cells(tmp_path):
    app=fc.FutureCrash.__new__(fc.FutureCrash)
    app.signal=fc.SignalCanvas(history_path=tmp_path/'history.json');app.signal.demo()
    app.signal_style='normal';normal=app.render_signal_panel(40,12)
    app.signal_style='negative';negative=app.render_signal_panel(40,12)
    assert all(fc.CSI+'7m' not in line for line in (negative[0],negative[-1]))
    assert fc.CSI+'7m' in negative[1]
    assert [fc.strip_ansi(line) for line in normal[1:-1]]==[fc.strip_ansi(line) for line in negative[1:-1]]


def test_cli_style_override_and_ambient_help(monkeypatch):
    monkeypatch.setattr(fc.sys,'argv',['future-crash','--signal-style','negative'])
    assert fc.parse_args().signal_style=='negative'
    app=fc.FutureCrash.__new__(fc.FutureCrash);app.help_scroll=0
    assert 'negative Signal style' in fc.strip_ansi(app.render_help(100,60))
