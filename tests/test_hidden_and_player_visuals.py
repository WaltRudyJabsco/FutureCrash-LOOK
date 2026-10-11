import importlib.machinery
import importlib.util
import io
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import Mock

import pytest
from look import look_renderer as renderer, player_visuals

ROOT=Path(__file__).resolve().parents[1]


def test_cli_default_hidden_opt_in_and_legacy_opt_out(tmp_path):
    (tmp_path/'visible.txt').write_text('hello')
    (tmp_path/'.secret.txt').write_text('secret')
    def run(*args):
        return subprocess.check_output([sys.executable,str(ROOT/'look/lk'),*args],cwd=tmp_path,text=True)
    assert '.secret.txt' not in run()
    assert '.secret.txt' not in run(str(tmp_path))
    assert '.secret.txt' in run('--hidden')
    assert '.secret.txt' in run('hidden')  # lh uses this entry point
    assert '.secret.txt' not in run('--no-hidden')


def test_recursive_catalog_hides_hidden_ancestors_but_not_search_root(tmp_path):
    root=tmp_path/'.workspace'
    paths=[root/'notes.txt', root/'.secret'/'notes.txt', root/'visible'/'.notes.txt']
    assert renderer._catalog_matches(paths,'notes',False,root)==paths[:1]
    assert renderer._catalog_matches(paths,'notes',True,root)==paths


class Terminal(io.StringIO):
    def isatty(self): return True


def terminal(monkeypatch, module):
    monkeypatch.setattr(module.sys,'stdin',Mock(isatty=lambda:True,fileno=lambda:0))
    monkeypatch.setattr(module.sys,'stdout',Terminal())
    monkeypatch.setattr(module.termios,'tcgetattr',lambda fd:[])
    monkeypatch.setattr(module.termios,'tcsetattr',lambda *args:None)
    monkeypatch.setattr(module.tty,'setcbreak',lambda fd:None)


def test_shift_h_preserves_filter_query_and_refreshes_candidates(tmp_path,monkeypatch):
    terminal(monkeypatch,renderer)
    monkeypatch.setattr(renderer,'NativePreviewController',Mock)
    keys=iter(['H','Q']); monkeypatch.setattr(renderer,'read_key',lambda **kw:next(keys))
    paths=[tmp_path/'notes',tmp_path/'.notes']
    for p in paths: p.mkdir()
    hidden=False; queries=[]
    def toggle():
        nonlocal hidden
        hidden=not hidden
        return 'hidden shown'
    def candidates(query):
        queries.append((query,hidden))
        return paths if hidden else paths[:1]
    renderer.pager(['rows'],24,80,rebuild=lambda *args:['rows'],candidates=candidates,
                   on_hidden=toggle,force_interactive=True,initial_query='notes')
    assert hidden
    assert ('notes',False) in queries and ('notes',True) in queries
    assert not any(query!='notes' for query,_ in queries)


@pytest.mark.parametrize('mode',[*range(1,7),8,9,10,11])
def test_ambient_frames_animate_stay_bounded_and_pause(mode):
    for width,height in [(1,1),(18,7),(120,35)]:
        a=player_visuals.frame(mode,width,height,1.3)
        assert len(a)==height and all(len(row)==width for row in a)
    assert player_visuals.frame(mode,80,24,1.3)!=player_visuals.frame(mode,80,24,3.7)
    assert player_visuals.frame(mode,80,24,1.3,False)==player_visuals.frame(mode,80,24,3.7,False)


@pytest.fixture
def lk():
    loader=importlib.machinery.SourceFileLoader('lk_visual_test',str(ROOT/'look/lk'))
    spec=importlib.util.spec_from_loader(loader.name,loader)
    module=importlib.util.module_from_spec(spec); loader.exec_module(module)
    return module


def test_player_cycles_all_views_without_losing_transport_controls(lk,monkeypatch):
    terminal(monkeypatch,lk)
    modes=[]; calls=[]
    monkeypatch.setattr(lk,'_media_player_render',lambda mode=0,visual_elapsed=0:modes.append(mode) or 'frame')
    keys=iter(['v']*(len(player_visuals.NAMES)+1)+[' ','n','p','left','right','s','r','x','q'])
    monkeypatch.setattr(lk,'_read_tty_key',lambda *args:next(keys))
    monkeypatch.setattr(lk,'_media_control_session',lambda action:calls.append(action))
    monkeypatch.setattr(lk,'_media_mpv_request',lambda args:calls.append(args))
    monkeypatch.setattr(lk,'_media_shuffle_command',lambda:calls.append('shuffle'))
    monkeypatch.setattr(lk,'_media_repeat_command',lambda args:calls.append('repeat'))
    assert lk.media_player()==0
    assert modes[:len(player_visuals.NAMES)+2]==list(range(len(player_visuals.NAMES)+1))+[0]
    assert calls==['toggle','next','prev',['seek',-10,'relative'],['seek',10,'relative'],'shuffle','repeat','stop']


def test_cycle_holds_each_visual_ten_seconds_and_includes_album_art():
    mode=player_visuals.CYCLE_MODE
    assert [player_visuals.active_mode(mode,seconds) for seconds in (0,9.99,10,60,69.99,70,79.99,80,89.99,90,99.99,100,109.99,110)]==[1,1,2,7,7,8,8,9,9,10,10,11,11,1]
    assert all(player_visuals.active_mode(mode,second)!=0 for second in range(200))
    for fixed in range(mode):assert player_visuals.active_mode(fixed,120)==fixed


def test_cycle_uses_album_renderer_and_keeps_transport_footer(lk,monkeypatch):
    snap={'entry':{'artist':'Artist','title':'Song'},'state':'playing','position':30,'duration':60,
          'index':0,'session':{'queue':[{}]}}
    monkeypatch.setattr(lk.shutil,'get_terminal_size',lambda fallback:os.terminal_size((100,30)))
    monkeypatch.setattr(lk,'_media_player_large_art',lambda entry,w,h:['@'*w]*h)
    rendered=lk._media_player_full_visual(snap,player_visuals.CYCLE_MODE,60)
    assert 'Cycle · Album Art' in rendered and '@' in rendered
    assert 'space pause' in rendered and 'p/n previous/next' in rendered


def test_selecting_cycle_starts_its_own_timer(lk,monkeypatch):
    terminal(monkeypatch,lk)
    clock=[100.0];frames=[]
    monkeypatch.setattr(lk.time,'monotonic',lambda:clock[0])
    monkeypatch.setattr(lk,'_media_player_render',lambda mode=0,visual_elapsed=0:frames.append((mode,visual_elapsed)) or 'frame')
    keys=iter([('v',1000.0),('',1009.0),('',1010.0),('q',1010.0)])
    def key(*args):
        value,clock[0]=next(keys)
        return value
    monkeypatch.setattr(lk,'_read_tty_key',key)
    assert lk.media_player(initial_visualizer=player_visuals.CYCLE_MODE-1)==0
    assert frames[1:]==[(player_visuals.CYCLE_MODE,age) for age in (0.0,9.0,10.0)]


def test_full_visual_keeps_metadata_within_terminal(lk,monkeypatch):
    snap={'entry':{'artist':'Artist','title':'Song'},'state':'playing','position':30,'duration':60,
          'index':0,'session':{'queue':[{}]}}
    for columns,lines in [(20,10),(120,40)]:
        monkeypatch.setattr(lk.shutil,'get_terminal_size',lambda fallback:os.terminal_size((columns,lines)))
        rendered=lk._media_player_full_visual(snap,1)
        rows=rendered.splitlines()
        assert len(rows)<=lines-1
        assert all(len(lk._strip_ansi(row))<=columns-1 for row in rows)
    assert 'ambient animation' in rendered and 'Queue 1/1' in rendered


def test_lh_migrates_owned_home_shortcut_but_preserves_user_function():
    import shutil
    zsh=shutil.which('zsh')
    if not zsh: pytest.skip('zsh unavailable')
    source=(ROOT/'look/zshrc').read_text()
    def function(name):
        start=source.index(name+'() {')
        return source[start:source.index('\n}',start)+2]
    start=source.index("# Migrate only LOOK's old home shortcut")
    end=source.index("_look_short_install lh '_look hidden'",start)+len("_look_short_install lh '_look hidden'")
    setup='_LOOK_SHORTCUT_POLICY=respect\n_look() { print -r -- "$@"; }\n'
    setup+=function('_look_short_name_kind')+'\n'+function('_look_short_install')+'\n'
    for old,expected in [('lh() { _look home "$@"; }','hidden /tmp'),('lh() { print custom; }','custom')]:
        output=subprocess.check_output([zsh,'-f','-c',setup+old+'\n'+source[start:end]+'\nlh /tmp'],text=True).strip()
        assert output==expected


def test_large_album_art_uses_available_canvas_and_caches_decode(lk,monkeypatch,tmp_path):
    cover=tmp_path/'cover.jpg';cover.write_bytes(b'cover')
    calls=[]
    monkeypatch.setattr(lk.media_art,'artwork_for',lambda source:cover)
    monkeypatch.setattr(lk.media_art,'ascii_lines',lambda source,w,h:calls.append((w,h)) or ['@'*w]*h)
    monkeypatch.setattr(lk.shutil,'get_terminal_size',lambda fallback:os.terminal_size((100,30)))
    snap={'entry':{'path':str(cover),'artist':'Artist','title':'Song'},'state':'paused','position':30,'duration':60,
          'index':0,'session':{'queue':[{}]}}
    first=lk._media_player_full_visual(snap,7)
    assert 'Album Art' in first and 'PAUSED' in first and 'Queue 1/1' in first
    assert calls==[(99,24)]
    assert first==lk._media_player_full_visual(snap,7) and len(calls)==1
    assert len(first.splitlines())==29


def test_large_remote_album_art_queues_fetch_without_blocking(lk,monkeypatch):
    calls=[]
    monkeypatch.setattr(lk,'_media_remote_cover_path',lambda row,fetch=False:None)
    monkeypatch.setattr(lk,'_media_remote_preview_identity',lambda row:{'node':'remote','id':'track','path':'/music/song.flac','mtime':1})
    monkeypatch.setattr(lk,'_media_queue_remote_preview',lambda row,w,h:calls.append((w,h)))
    lines=lk._media_player_large_art({'node':'remote'},100,30)
    assert calls==[(80,24)] and len(lines)==30
    assert all(len(line)==100 for line in lines)
    assert any('Loading album art' in line for line in lines)


def test_large_album_art_missing_cover_has_clear_fallback(lk,monkeypatch):
    monkeypatch.setattr(lk,'_media_remote_cover_path',lambda row,fetch=False:None)
    monkeypatch.setattr(lk,'_media_remote_preview_identity',lambda row:None)
    monkeypatch.setattr(lk,'_media_queue_remote_preview',lambda *args:False)
    lines=lk._media_player_large_art({},60,12)
    assert any('Album art unavailable' in line for line in lines)
    assert len(lines)==12


def test_album_colors_change_on_each_transition_including_hash_collision(lk,monkeypatch):
    visuals=lk.player_visuals
    monkeypatch.setattr(visuals,'_album_track',None)
    snap={'entry':{'album':'Same','title':'First','path':'/first'},'index':0}
    first=visuals.album_color(snap)
    assert first==visuals.album_color(dict(snap,state='paused',position=40))
    # Every distinct identity must change color, even when hashes collide.
    for index in range(100):
        snap={'entry':{'album':'Same','title':str(index),'path':'/'+str(index)},'index':index}
        current=visuals.album_color(snap)
        assert current!=first
        assert current==visuals.album_color(snap)
        first=current


def test_black_hole_has_dark_horizon_and_seeded_disc():
    a=player_visuals.frame(8,80,24,2,seed=1)
    assert a[11][39:41]=='  '
    assert any('@' in row or '#' in row for row in a)
    assert a==player_visuals.frame(8,80,24,2,seed=1)
    assert a!=player_visuals.frame(8,80,24,2,seed=2)


def test_album_shimmer_moves_diagonally_without_changing_text():
    line='@'*80
    def highlighted(y,elapsed):
        spans=player_visuals.shimmer_spans(line,y,80,24,elapsed)
        assert ''.join(text for text,_ in spans)==line
        return sum(len(text) for text,bright in spans if bright)
    assert highlighted(0,5)>0 and highlighted(23,5)==0
    assert highlighted(23,7.99)>0 and highlighted(0,7.99)==0
    assert 0<highlighted(12,6.5)<25
    for elapsed in (0,4.99,8,17.99):
        assert player_visuals.shimmer_spans(line,0,80,24,elapsed)==[(line,False)]
    assert player_visuals.shimmer_spans(line,0,80,24,5,False)==[(line,False)]


def test_album_shimmer_preserves_terminal_width_and_transport(lk,monkeypatch):
    snap={'entry':{'title':'Song'},'state':'playing','position':0,'duration':60,
          'index':0,'session':{'queue':[{}]}}
    monkeypatch.setattr(lk.shutil,'get_terminal_size',lambda fallback:os.terminal_size((80,24)))
    monkeypatch.setattr(lk,'_media_player_large_art',lambda entry,w,h:['@'*w]*h)
    monkeypatch.setattr(lk,'_c',lambda text,code:'\x1b['+code+'m'+text+'\x1b[0m')
    idle=lk._media_player_full_visual(snap,7,0)
    sweep=lk._media_player_full_visual(snap,7,6.5)
    assert idle!=sweep and lk._strip_ansi(idle)==lk._strip_ansi(sweep)
    assert all(len(lk._strip_ansi(row))==79 for row in sweep.splitlines())
    assert 'space pause' in lk._strip_ansi(sweep)


def test_rooftops_runner_clears_gap_and_lands_on_roof():
    width,height=90,24
    span=width//3;gap=span//5;anchor=int(width*.28)
    # At the middle of a gap the runner rises; on solid roof it returns.
    def scene(world):
        phase=(world-anchor-1)/player_visuals.ROOFTOP_SPEED
        return player_visuals.frame(9,width,height,phase,seed=3)
    ground=scene(span*2+12)
    airborne=scene(span*2+span-gap/2)
    assert ground[height-6][anchor:anchor+3]==' o '
    head=next(y for y,row in enumerate(airborne) if row[anchor:anchor+3]==' o ')
    assert head<height-6
    assert airborne[height-3][anchor+1]!='='
    assert ground[height-3][anchor+1]=='='
    assert ground==scene(span*2+12)
    assert ground!=player_visuals.frame(9,width,height,2,seed=4)


def test_cycle_rooftops_keeps_track_and_transport(lk,monkeypatch):
    snap={'entry':{'title':'City Song'},'state':'playing','position':2,'duration':60,
          'index':0,'session':{'queue':[{}]}}
    monkeypatch.setattr(lk.shutil,'get_terminal_size',lambda fallback:os.terminal_size((100,30)))
    text=lk._strip_ansi(lk._media_player_full_visual(snap,player_visuals.CYCLE_MODE,80))
    assert 'Cycle · Rooftops' in text and 'City Song' in text and 'space pause' in text
    assert len(text.splitlines())==29


def test_spectrum_has_bar_tops_and_fading_sparks():
    rows=player_visuals.frame(10,80,24,3.7,seed=2)
    assert any('*' in row or ':' in row or '.' in row for row in rows)
    assert sum(row.count('=') for row in rows)>=20
    assert player_visuals.spectrum_color(0,24)!=player_visuals.spectrum_color(23,24)
    assert all(player_visuals.spectrum_color(y,24) in player_visuals.SPECTRUM_COLORS for y in range(24))


def test_black_hole_ufo_is_occasional_and_pauses():
    mode=8;phase=player_visuals.UFO_DELAY_SECONDS+player_visuals.UFO_FLIGHT_SECONDS/2
    rows=player_visuals.frame(mode,80,24,phase)
    assert any('(o---o)' in row for row in rows)
    assert not any('(o---o)' in row for row in player_visuals.frame(mode,80,24,0))
    assert not any('(o---o)' in row for row in player_visuals.frame(mode,80,24,phase,False))
    assert not any('(o---o)' in row for row in player_visuals.frame(mode,80,24,phase+player_visuals.UFO_FLIGHT_SECONDS))


def test_spectrum_renderer_uses_gradient_without_expanding_rows(lk,monkeypatch):
    snap={'entry':{'title':'City Song'},'state':'playing','position':2,'duration':60,
          'index':0,'session':{'queue':[{}]}}
    monkeypatch.setattr(lk.shutil,'get_terminal_size',lambda fallback:os.terminal_size((80,24)))
    monkeypatch.setattr(lk,'_c',lambda text,code:'\x1b['+code+'m'+text+'\x1b[0m')
    text=lk._media_player_full_visual(snap,10,3.7)
    assert player_visuals.SPECTRUM_COLORS[0] in text and player_visuals.SPECTRUM_COLORS[-1] in text
    plain=lk._strip_ansi(text)
    assert all(len(row)==79 for row in plain.splitlines())
    assert 'space pause' in plain and 'Spectrum' in plain
