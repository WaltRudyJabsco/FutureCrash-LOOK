import sys
import types
from pathlib import Path
from unittest.mock import Mock
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'look'))
import player_visuals
import saver
import saver_text
import terminal_style


@pytest.fixture(autouse=True)
def private_captions(tmp_path,monkeypatch):
    monkeypatch.setattr(saver_text,'path',lambda:tmp_path/'captions.json')
    saver_text.read.cache_clear()
    yield
    saver_text.read.cache_clear()


@pytest.mark.parametrize('name',['Flight Deck','Signal Bloom'])
@pytest.mark.parametrize('size',[(1,1),(20,8),(80,24),(240,80)])
def test_scenes_are_bounded_deterministic_and_animate(name,size):
    mode=player_visuals.NAMES.index(name)+1
    width,height=size
    frame=player_visuals.frame(mode,width,height,1,True,12)
    assert len(frame)==height and all(len(line)==width for line in frame)
    assert frame==player_visuals.frame(mode,width,height,1,True,12)
    assert player_visuals.frame(mode,width,height,1,False,12)==player_visuals.frame(mode,width,height,8,False,12)
    if width>=80:assert frame!=player_visuals.frame(mode,width,height,10,True,12)


def test_flight_deck_has_alternating_inverse_bands():
    early=player_visuals.flight_deck_inverse_rows(40,1)
    later=player_visuals.flight_deck_inverse_rows(40,9)
    assert early>later and {0,1,38,39}.issubset(later)


def test_bridge_inks_have_readable_contrast():
    palette=terminal_style.THEMES['bridge']
    for ink in palette['accents'].values():assert terminal_style.contrast(palette['background'],ink)>=4.5


def test_ai_caption_generation_is_explicit_cached_and_bounded(monkeypatch):
    infer=Mock(return_value={'message':{'content':'DISTANT SIGNAL\nWE KEEP WATCH\nTHE QUIET RETURNS\n\x1b[31mBAD'}})
    monkeypatch.setitem(sys.modules,'fabric_client',types.SimpleNamespace(infer=infer))
    assert saver_text.generate()==0
    assert saver_text.read()==('DISTANT SIGNAL','WE KEEP WATCH','THE QUIET RETURNS')
    infer.assert_called_once()
    for i in range(10):player_visuals.flight_deck_frame(80,24,i,0)
    infer.assert_called_once()  # Playback never triggers inference.
    assert infer.call_args.kwargs['timeout']==45
    assert saver_text.reset()==0 and not saver_text.read()


def test_bad_generation_retains_existing_cache(monkeypatch):
    saver_text.path().write_text('{"phrases":["KEEP THIS CAPTION"]}')
    infer=Mock(return_value={'message':{'content':'x'}})
    monkeypatch.setitem(sys.modules,'fabric_client',types.SimpleNamespace(infer=infer))
    with pytest.raises(ValueError):saver_text.generate()
    assert saver_text.read()==('KEEP THIS CAPTION',)


def test_malformed_cache_falls_back_without_crashing():
    saver_text.path().write_text('{broken')
    assert not saver_text.read()
    assert player_visuals.flight_deck_frame(80,24,2)


def test_new_matching_display_inherits_live_control_choices():
    settings={**saver.defaults(),'independent':False,'scene':'Stars'}
    old=saver.SceneRun(settings,42);old.sample(21,80,24)
    old.next_scene(elapsed=21);old.next_color()
    new=saver.SceneRun(settings,42);new.copy_controls_from(old)
    assert old.sample(22,80,24)==new.sample(22,80,24)
