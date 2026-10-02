from pathlib import Path

LK=(Path(__file__).parents[1]/"look"/"lk").read_text(encoding="utf-8")


def test_bare_preview_auditions_configured_default_not_personality_resolution():
    block=LK[LK.index('def _voice_command'):LK.index('def _settings_pick_voice')]
    assert 'voice=args[1].casefold() if len(args)>=2 else cfg["voice"]' in block


def test_settings_preview_label_shows_configured_default_voice():
    assert '("voicepreview","SPEECH","Preview voice",_load_speech_config()["voice"],' in LK


def test_alert_cli_keeps_named_target_explicit():
    block=LK[LK.index('def _alert_command'):LK.index('def _voice_command')]
    assert 'startswith("@")' in block
    assert '"--target",target' in block
