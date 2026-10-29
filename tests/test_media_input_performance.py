"""Prepared filtering preserves results; slow previews cannot hold terminal input."""
import os
import pty
import re
import select
import termios
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest
from media_ui_work import LatestWork
from test_media_request_regressions import lk


def projection(rows):
    return [(r.get('node'),r.get('id'),r.get('hidden'),r.get('source_count'),
             [(s.get('node'),s.get('id')) for s in r.get('sources',[])]) for r in rows]


@pytest.mark.parametrize('show_hidden',[False,True])
@pytest.mark.parametrize('show_all',[False,True])
def test_prepared_find_retains_original_matching_and_collapse(lk,monkeypatch,show_hidden,show_all):
    rules={'hidden_paths':['/hidden/song.mp3'],'hidden_trees':['/samples']}
    monkeypatch.setattr(lk,'_media_visibility',lambda:rules)
    rows=[{'node':'one','id':str(i),'path':path,'title':title,'artist':'Björk','bytes':i}
          for i,(path,title) in enumerate([('/music/a.mp3','alpha'),('/hidden/song.mp3','beta'),('/samples/a.mp3','sample'),('/music/b.mp3','beta')])]
    rows.append(dict(rows[0],locations=[dict(rows[0]),dict(rows[0],node='two',id='copy',path='/other/alpha.mp3')]))
    plan=lk._MediaQueryPlan(rows,show_hidden)
    for query in ('','alpha','beta','björk','\\alpha','björk \\beta','/other','\\'):
        expected=lk._media_collapse(lk._media_filter_rows(rows,query),show_all=show_all,show_hidden=show_hidden)
        assert projection(plan.find(query,show_all))==projection(expected)


def test_player_reuses_visibility_and_sort_work_while_typing(lk,monkeypatch):
    rows=[{'node':'one','id':str(i),'path':f'/music/{i}.mp3','title':'beastie '+str(i)} for i in range(500)]
    monkeypatch.setattr(lk,'_media_visibility',lambda:{'hidden_paths':[]})
    hidden_calls=[];sort_calls=[]
    monkeypatch.setattr(lk,'_media_is_hidden',lambda *a:hidden_calls.append(1) or False)
    original=lk._media_find_order
    monkeypatch.setattr(lk,'_media_find_order',lambda *a:sort_calls.append(1) or original(*a))
    plan=lk._MediaQueryPlan(rows)
    for query in ('b','be','bea','beastie'):assert len(plan.player('library',query,'audio',1))==500
    assert len(hidden_calls)==500 and len(sort_calls)==1


def test_latest_preview_drops_obsolete_results_and_never_queues_a_backlog():
    work=LatestWork();gate=threading.Event();started=threading.Event();calls=[]
    def first():
        started.set();gate.wait(2);return 'obsolete'
    try:
        assert work.get('first',first,default='loading')=='loading'
        assert started.wait(1)
        for i in range(100):work.get(str(i),lambda i=i:calls.append(i) or i,default='loading')
        gate.set()
        deadline=time.monotonic()+1
        while time.monotonic()<deadline:
            value=work.get('99',lambda:99,default='loading',ttl=10)
            if value==99:break
            time.sleep(.005)
        assert value==99 and calls==[99]
    finally:gate.set();work.close()


def test_background_transport_snapshot_does_not_rewrite_queue(lk,monkeypatch):
    session={'queue':[{'id':'one'}],'current_index':0,'state':'paused'}
    monkeypatch.setattr(lk,'_media_session',lambda:dict(session))
    monkeypatch.setattr(lk,'_media_mpv_alive',lambda:True)
    monkeypatch.setattr(lk,'_media_mpv_loaded',lambda:True)
    monkeypatch.setattr(lk,'_media_mpv_property',lambda key:{'playlist-pos':0,'idle-active':False,'pause':True,'time-pos':5,'duration':10}.get(key))
    monkeypatch.setattr(lk,'_media_save_session',lambda *_:pytest.fail('background status must never overwrite queue edits'))
    assert lk._media_status_snapshot(read_only=True)['position']==5


@pytest.mark.parametrize('surface',['audio','video','find'])
@pytest.mark.parametrize('typed,expected',[
    (b'/beastix\x7fe bj\xc3\xb6rk','beastie björk'),
    (b'/Cairo','Cairo'),
    (b'/\x1b[99;2u\x1b[99;2:3u\x1b[97u\x1b[105u\x1b[114u\x1b[111u','Cairo'),
    (b'/\x1b[200~Cairo\nBj\xc3\xb6rk QWERTY\x1b[201~','Cairo Björk QWERTY'),
])
def test_real_terminal_keeps_typing_while_art_and_ipc_are_slow(surface,typed,expected,tmp_path):
    root=Path(__file__).resolve().parents[1]
    script=r'''
import importlib.machinery,importlib.util,os,sys,time
sys.path.insert(0,sys.argv[1]+'/look')
l=importlib.machinery.SourceFileLoader('input_test',sys.argv[1]+'/look/lk');s=importlib.util.spec_from_loader(l.name,l);m=importlib.util.module_from_spec(s);l.exec_module(m)
kind=sys.argv[2]
rows=[{'node':'local','id':str(i),'path':'/missing/'+str(i)+('.mkv' if kind=='video' else '.mp3'),'title':'beastie '+str(i),'media_type':'video/matroska' if kind=='video' else 'audio/mpeg'} for i in range(1000)]
m._media_catalog_entries=lambda:(rows,{'nodes':[{'node':'local'}]})
m._media_visibility=lambda:{'hidden_paths':[]}
m._media_session=lambda:None
def unexpected(*a,**kw):raise AssertionError('search text invoked a command')
for name in ('_media_queue_append','_media_launch_from_library','_media_choose_hide_directory','_media_reset_audio','_media_open_with','media_player','_media_control_session','_media_shuffle_command','_media_repeat_command','_media_keep_offline','_media_edit_prompt','_media_refresh_rows'):
 setattr(m,name,unexpected)
m.terminal_style.open_pane=unexpected
m._media_status_snapshot=lambda **kw:time.sleep(2)
m._media_cover_lines=lambda *a,**kw:time.sleep(2) or []
m._media_native_art=lambda *a:None
m._media_remote_preview_state=lambda *a:('unavailable','')
m.shutil.get_terminal_size=lambda *_:os.terminal_size((120,34))
class Preview:
 enabled=False
 def invalidate(self):pass
 def frame_cleared(self):pass
 def request(self,*a):pass
 def paint_ready(self):pass
m.NativePreviewController=Preview
class Durations:
 def __init__(self,*a):pass
 def value(self,row):return None
 def poll(self,*a):return False
 def close(self):pass
m.DurationPreview=Durations
if kind=='find':m._media_selector(rows,catalog_meta={'nodes':[{'node':'local'}]})
else:m._media_player_library(media_kind=kind)
'''
    master,slave=pty.openpty()
    process=subprocess.Popen([sys.executable,'-u','-c',script,str(root),surface],stdin=slave,stdout=slave,stderr=slave,cwd=tmp_path,start_new_session=True)
    os.close(slave);captured=b''
    def until(needle,seconds):
        nonlocal captured
        deadline=time.monotonic()+seconds
        while time.monotonic()<deadline:
            plain=re.sub(rb'\x1b\[[0-?]*[ -/]*[@-~]',b'',captured)
            if needle in plain:return True
            ready,_,_=select.select([master],[],[],.02)
            if ready:
                try:captured+=os.read(master,65536)
                except OSError:break
        return needle in re.sub(rb'\x1b\[[0-?]*[ -/]*[@-~]',b'',captured)
    try:
        assert until(b'FILTER',5),captured[-1000:]
        if surface=='find':
            os.write(master,b'I');assert until(b'MEDIA INFO',1)
        captured=b''
        os.write(master,b'\x1b[?1;2c\x1b_Gi=42;OK\x1b\\'+typed)
        needle=('FILTER ' if surface=='find' else 'SEARCH /').encode()+expected.encode()
        assert until(needle,1.2),captured[-1000:]
        attrs=termios.tcgetattr(master);attrs[3]&=~termios.ISIG
        termios.tcsetattr(master,termios.TCSANOW,attrs)
        os.write(master,b'\x03')
        deadline=time.monotonic()+1
        while process.poll() is None and time.monotonic()<deadline:
            ready,_,_=select.select([master],[],[],.01)
            if ready:
                try:os.read(master,65536)
                except OSError:break
        process.wait(timeout=.5)
    finally:
        if process.poll() is None:process.kill();process.wait()
        os.close(master)


def test_conflicting_duplicate_visibility_retains_first_matching_source(lk,monkeypatch):
    monkeypatch.setattr(lk,'_media_visibility',lambda:{'hidden_paths':[]})
    rows=[{'node':'owner','id':'hidden','path':'/same.mp3','title':'hidden discovery','fabric_hidden_by':'/same.mp3'},
          {'node':'owner','id':'visible','path':'/same.mp3','title':'visible discovery'}]
    plan=lk._MediaQueryPlan(rows)
    for query in ('','hidden','visible'):
        expected=lk._media_collapse(lk._media_filter_rows(rows,query))
        assert projection(plan.find(query))==projection(expected)
