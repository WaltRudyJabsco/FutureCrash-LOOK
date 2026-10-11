from pathlib import Path
import sys
import wave
import array
from contextlib import contextmanager
from unittest.mock import Mock
import os
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'look'))
import games as g


def test_demo_survives_many_gaps_and_replays_exactly():
    a=g.rooftops_initial('0p',42);b=g.rooftops_initial('0p',42)
    for _ in range(6000):g.rooftops_step(a);g.rooftops_step(b)
    assert a==b and a.runners[0].alive and a.distance>1000


def test_missing_jump_falls_and_cannot_land_from_below():
    run=g.rooftops_initial()
    for _ in range(300):g.rooftops_step(run)
    assert not run.runners[0].alive and run.runners[0].height<g.ROOFTOPS_FALL_LIMIT
    saved=run.distance
    for _ in range(30):g.rooftops_step(run,[0])
    assert run.distance==saved


def test_two_player_input_is_independent_and_longest_run_wins():
    run=g.rooftops_initial('2p')
    for _ in range(300):
        slot=(run.distance+g.ROOFTOPS_ANCHOR+1)%g.ROOFTOPS_SPAN
        g.rooftops_step(run,[0] if slot>=g.ROOFTOPS_SPAN-g.ROOFTOPS_GAP-3 else [])
    assert run.runners[0].alive and not run.runners[1].alive
    for _ in range(360):g.rooftops_step(run)
    assert 'P1 WINS' in g.rooftops_result(run)
    tie=g.rooftops_initial('2p')
    for _ in range(300):g.rooftops_step(tie)
    assert 'DRAW' in g.rooftops_result(tie)


def test_jump_cannot_reset_velocity_in_midair():
    run=g.rooftops_initial();g.rooftops_step(run,[0])
    velocity=run.runners[0].velocity
    g.rooftops_step(run,[0])
    assert run.runners[0].velocity<velocity


@pytest.mark.parametrize('mode',['0p','1p','2p'])
def test_render_bounded_and_reuses_silent_visual_scene(mode):
    run=g.rooftops_initial(mode,3)
    for w,h in ((1,1),(30,10),(80,24),(240,80)):
        rows=g.rooftops_lines(run,w,h)
        assert len(rows)<=h and all(len(r)==w for r in rows)
    text='\n'.join(g.rooftops_lines(run,80,30))
    assert 'seed 3' in text and 'M music' in text
    assert ('Z P1' in text and '/ P2' in text) if mode=='2p' else True


def test_original_soundtrack_is_repeatable_valid_nonempty_pcm(tmp_path):
    a=tmp_path/'a.wav';b=tmp_path/'b.wav'
    g.rooftops_soundtrack(a);g.rooftops_soundtrack(b)
    assert a.read_bytes()==b.read_bytes()
    with wave.open(str(a)) as source:
        assert (source.getnchannels(),source.getsampwidth(),source.getframerate())==(2,2,g.ROOFTOPS_MUSIC_RATE)
        assert source.getnframes()==round(g.ROOFTOPS_MUSIC_RATE*60/g.ROOFTOPS_MUSIC_BPM*g.ROOFTOPS_MUSIC_BEATS)
        pcm=array.array('h');pcm.frombytes(source.readframes(source.getnframes()))
    assert any(pcm) and max(abs(v) for v in pcm)<32767


def test_game_music_owns_and_cleans_only_its_process(monkeypatch,tmp_path):
    process=Mock();process.poll.return_value=None
    launch=Mock(return_value=process)
    monkeypatch.setattr(g.shutil,'which',lambda name:'/usr/bin/mpv')
    monkeypatch.setattr(g.subprocess,'Popen',launch)
    monkeypatch.setattr(g,'rooftops_soundtrack',lambda p:p.write_bytes(b'wav'))
    music=g.RooftopsMusic();music.sync(True)
    path=music.path
    assert path.exists() and '--loop-file=inf' in launch.call_args.args[0]
    music.sync(True);assert launch.call_count==1
    music.sync(False);process.terminate.assert_called_once()
    music.enabled=False;music.sync(True);assert launch.call_count==1
    music.close();assert not path.exists()


def test_missing_mpv_keeps_game_usable(monkeypatch):
    monkeypatch.setattr(g.shutil,'which',lambda name:None)
    music=g.RooftopsMusic();music.sync(True)
    assert music.status=='unavailable' and music.process is None
    music.close()


@pytest.mark.parametrize('keys,expected',[(['z','/','q'],g.MENU_RETURN),(['p','p','r','m','s'],0),(['h','q'],g.MENU_RETURN)])
def test_game_loop_keys_and_audio_cleanup(monkeypatch,keys,expected):
    @contextmanager
    def terminal():yield 0
    monkeypatch.setattr(g,'terminal',terminal)
    monkeypatch.setattr(g.shutil,'get_terminal_size',lambda fallback:os.terminal_size((80,30)))
    class Clock:
        time=0
        def now(self):self.time+=g.ROOFTOPS_DT;return self.time
    monkeypatch.setattr(g.time,'monotonic',Clock().now)
    sequence=iter(keys)
    monkeypatch.setattr(g,'read_key',lambda fd,timeout=None:next(sequence,None))
    monkeypatch.setattr(g,'help_screen',Mock())
    music=Mock(status='off');music.enabled=False
    monkeypatch.setattr(g,'RooftopsMusic',lambda:music)
    assert g.play_rooftops('2p')==expected
    music.close.assert_called_once()


def test_two_jump_keys_reach_same_simulation_tick(monkeypatch):
    @contextmanager
    def terminal():yield 0
    monkeypatch.setattr(g,'terminal',terminal)
    monkeypatch.setattr(g.shutil,'get_terminal_size',lambda fallback:os.terminal_size((80,30)))
    clock=iter([0,.04,.08,.12]);monkeypatch.setattr(g.time,'monotonic',lambda:next(clock))
    keys=iter(['z','/',None,'q']);monkeypatch.setattr(g,'read_key',lambda *args:next(keys,None))
    music=Mock(status='off');music.enabled=False;monkeypatch.setattr(g,'RooftopsMusic',lambda:music)
    calls=[];step=g.rooftops_step
    def record(run,jumps):calls.append(set(jumps));step(run,jumps)
    monkeypatch.setattr(g,'rooftops_step',record)
    assert g.play_rooftops('2p')==g.MENU_RETURN
    assert calls[0]=={0,1} and calls[1]==set()


def test_menu_dispatch_and_aliases(monkeypatch):
    play=Mock(return_value=0);monkeypatch.setattr(g,'play_rooftops',play)
    monkeypatch.setattr(g,'wopr_say',Mock())
    assert ('6','ROOFTOPS','rooftops') in g._GAME_ITEMS
    for name in ('rooftops','roof','roofs','rooftop'):
        assert g.run([name,'2p'])==0
    assert all(call.args==('2p',) for call in play.call_args_list)


def test_roofs_allow_five_seconds_of_ground_between_gaps():
    assert g.ROOFTOPS_SPAN-g.ROOFTOPS_GAP>=60
    assert (g.ROOFTOPS_SPAN-g.ROOFTOPS_GAP)/g.player_visuals.ROOFTOP_SPEED>=5
    run=g.rooftops_initial()
    for _ in range(180):g.rooftops_step(run)
    assert run.runners[0].grounded and run.runners[0].alive
    # The visual floor and physics floor agree at the new long roof edge.
    run.distance=g.ROOFTOPS_SPAN-g.ROOFTOPS_GAP-g.ROOFTOPS_ANCHOR-1+1
    run.elapsed=run.distance/g.player_visuals.ROOFTOP_SPEED
    rows=g.rooftops_lines(run,80,24)
    assert rows[-5][g.ROOFTOPS_ANCHOR+1]!='='


def test_music_status_does_not_claim_on_while_stopped(monkeypatch):
    monkeypatch.setattr(g.shutil,'which',lambda name:'/usr/bin/mpv')
    music=g.RooftopsMusic()
    assert music.status=='paused'
    music.enabled=False;assert music.status=='off'
    music.failed=True;assert music.status=='unavailable'


def test_game_roof_graphics_match_collision_gaps_across_entire_course():
    run=g.rooftops_initial()
    for offset in range(g.ROOFTOPS_SPAN):
        run.distance=float(offset);run.elapsed=run.distance/g.player_visuals.ROOFTOP_SPEED
        rows=g.rooftops_lines(run,80,24)
        slot=(offset+g.ROOFTOPS_ANCHOR+1)%g.ROOFTOPS_SPAN
        assert (rows[-5][g.ROOFTOPS_ANCHOR+1]=='=')==(slot<g.ROOFTOPS_SPAN-g.ROOFTOPS_GAP)


def test_running_course_does_not_drift_between_physics_and_drawing():
    run=g.rooftops_initial('0p')
    for _ in range(2000):
        g.rooftops_step(run)
        solid=(run.distance+g.ROOFTOPS_ANCHOR+1)%g.ROOFTOPS_SPAN<g.ROOFTOPS_SPAN-g.ROOFTOPS_GAP
        assert (g.rooftops_lines(run,80,24)[-5][g.ROOFTOPS_ANCHOR+1]=='=')==solid
