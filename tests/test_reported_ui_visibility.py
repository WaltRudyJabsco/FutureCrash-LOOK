import importlib.util
import io
import json
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from importlib.machinery import SourceFileLoader
from pathlib import Path
from types import SimpleNamespace

import pytest
from core import node
from look import look_renderer as renderer

ROOT=Path(__file__).resolve().parents[1]


def load_lk():
    spec=importlib.util.spec_from_loader('lk_reported_ui',SourceFileLoader('lk_reported_ui',str(ROOT/'look/lk')))
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


class Tty(io.StringIO):
    def isatty(self):
        return True


def test_concurrent_media_session_writes_use_separate_staging_files(tmp_path,monkeypatch):
    lk=load_lk()
    destination=tmp_path/'media_session.json'
    monkeypatch.setattr(lk,'MEDIA_SESSION_FILE',destination)
    barrier=threading.Barrier(2)
    replace=os.replace
    staged=[]

    def simultaneous_replace(source,target):
        staged.append(Path(source))
        # Reproduce Player and MP both finishing their writes before publishing.
        barrier.wait(timeout=5)
        return replace(source,target)

    monkeypatch.setattr(os,'replace',simultaneous_replace)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures=[pool.submit(lk._media_save_session,{'state':state})
                 for state in ['playing','paused']]
        for future in futures:
            future.result(timeout=10)
    assert len(set(staged))==2
    assert json.loads(destination.read_text())['state'] in {'playing','paused'}
    assert destination.stat().st_mode & 0o777 == 0o600
    assert list(tmp_path.glob('*.tmp'))==[]


def test_atomic_json_failure_preserves_previous_file_and_cleans_staging(tmp_path,monkeypatch):
    lk=load_lk()
    destination=tmp_path/'session.json'
    lk._atomic_json(destination,{'state':'playing'})

    def fail_replace(*args):
        raise OSError('simulated publication failure')

    monkeypatch.setattr(os,'replace',fail_replace)
    with pytest.raises(OSError,match='publication failure'):
        lk._atomic_json(destination,{'state':'paused'})
    assert json.loads(destination.read_text())=={'state':'playing'}
    assert list(tmp_path.glob('*.tmp'))==[]


@pytest.mark.parametrize('surface',['find','mp'])
@pytest.mark.parametrize('finish_search',[False,True])
def test_filtered_media_navigation_marking_and_select_all(tmp_path,monkeypatch,surface,finish_search):
    lk=load_lk()
    output=Tty()
    rows=[{'path':str(tmp_path/f'track{i:02d}.mp3'),'title':f'Track {i:02d}',
           'artist':'pharc','node':'m3','id':str(i)} for i in range(16)]
    rows.append({'path':str(tmp_path/'other.mp3'),'title':'Other','artist':'other','node':'m3','id':'other'})
    monkeypatch.setattr(lk.sys,'stdout',output)
    monkeypatch.setattr(lk.sys,'stdin',SimpleNamespace(isatty=lambda:True,fileno=lambda:0))
    monkeypatch.setattr(lk.termios,'tcgetattr',lambda fd:[])
    monkeypatch.setattr(lk.termios,'tcsetattr',lambda *args:None)
    monkeypatch.setattr(lk.tty,'setcbreak',lambda fd:None)
    monkeypatch.setattr(lk.shutil,'get_terminal_size',lambda fallback:os.terminal_size((80,32)))
    monkeypatch.setattr(lk,'_media_catalog_entries',lambda:(rows,{}))
    monkeypatch.setattr(lk,'_media_collapse',lambda rows,**kwargs:rows)
    monkeypatch.setattr(lk,'_media_mp_rows',lambda mode,rows,query:lk._media_filter_rows(rows,query))
    monkeypatch.setattr(lk,'_media_mp_now_playing',lambda width:'STOPPED')
    monkeypatch.setattr(lk,'_media_status_snapshot',lambda:None)
    monkeypatch.setattr(lk,'NativePreviewController',lambda:SimpleNamespace(
        frame_cleared=lambda:None,invalidate=lambda:None,paint_ready=lambda:None))
    queued=[]
    monkeypatch.setattr(lk,'_media_queue_append',lambda picked:queued.extend(picked) or len(picked))
    keys=['/',*'pharc']+(['esc'] if finish_search else [])+['down','\t','A',
            'Q' if surface=='find' else 'B','\x03']
    events=iter(keys)
    monkeypatch.setattr(lk,'_read_tty_key',lambda *args:next(events))
    if surface=='find':
        lk._media_selector(rows)
    else:
        lk.media_mp()
    assert [row['id'] for row in queued]==[str(i) for i in range(16)]
    # Tab must mark the row reached by Down, rather than the first search result.
    frames=lk._strip_ansi(output.getvalue())
    assert '✓ pharc — Track 01' in frames


def test_buffered_media_frames_keep_colors_and_pipes_stay_plain(monkeypatch):
    lk=load_lk()
    for terminal in [True,False]:
        destination=Tty() if terminal else io.StringIO()
        monkeypatch.setattr(lk.sys,'stdout',destination)
        buffer=lk._TerminalFrameBuffer()
        with lk.redirect_stdout(buffer):
            print(lk._c('LIBRARY','1;36'))
            print(lk._media_hints('Enter play · Q queue',80))
        assert ('\x1b[' in buffer.getvalue()) is terminal
        assert 'Enter' in buffer.getvalue()


def test_ff_header_is_not_a_selectable_result(tmp_path):
    paths=[tmp_path/'first',tmp_path/'second']
    view=renderer._catalog_view(paths,tmp_path,80,include_headers=False)
    assert len(view)==2
    assert 'first' in renderer.strip_ansi(view[0])
    assert 'LOOK FIND' not in renderer.strip_ansi(view[0])


def test_filter_and_wrapped_commands_fit_short_terminal(tmp_path,monkeypatch):
    output=Tty(); path=tmp_path/'song.mp3'; path.write_bytes(b'a')
    monkeypatch.setattr(renderer.sys,'stdout',output)
    monkeypatch.setattr(renderer.sys,'stdin',SimpleNamespace(isatty=lambda:True,fileno=lambda:0))
    monkeypatch.setattr(renderer.termios,'tcgetattr',lambda fd:[])
    monkeypatch.setattr(renderer.termios,'tcsetattr',lambda *args:None)
    monkeypatch.setattr(renderer.tty,'setcbreak',lambda fd:None)
    monkeypatch.setattr(renderer.shutil,'get_terminal_size',lambda fallback:os.terminal_size((70,18)))
    monkeypatch.setattr(renderer,'read_key',lambda **kwargs:'\x1b')
    monkeypatch.setattr(renderer,'NativePreviewController',lambda:SimpleNamespace(
        wakeup_fd=None,frame_cleared=lambda:None,request=lambda *args:None,
        invalidate=lambda:None,paint_ready=lambda:None,close=lambda:None))
    paths=[path]*160000
    renderer.pager([],18,70,force_interactive=True,initial_query='song',
        candidates=lambda q:paths,
        rebuild=lambda q,h=None,w=None,m=None:renderer._CatalogView(paths,[],tmp_path,w or 70,h,m),
        header_rows=lambda w:['LOOK FIND','header separator'])
    # Escape clears the query; use only the first complete frame.
    first=output.getvalue().split(renderer.CLEAR)[1]
    first=first.split(renderer.CLEAR)[0]
    assert first.count('\n')<18
    assert 'FILTER' in renderer.strip_ansi(first)
    assert 'Esc clear' in renderer.strip_ansi(first)


def test_owner_directory_visibility_survives_reload_and_is_node_scoped(tmp_path,monkeypatch):
    library=tmp_path/'media_library.json'
    library.write_text(json.dumps({'entries':[{'path':'/media/Junk/a.wav'},{'path':'/media/Junkyard/b.wav'}]}))
    monkeypatch.setattr(node,'LOOK_MEDIA_LIBRARY',library)
    monkeypatch.setattr(node,'identity',lambda:{'name':'m3'})
    node._local_media_route("visibility",{'path':'/media/Junk','tree':True,'hidden':True})
    rows=node._local_media_catalog()['entries']
    assert rows[0]['fabric_hidden_by']=='/media/Junk'
    assert not rows[1]['fabric_hidden_by']
    lk=load_lk()
    assert lk._media_is_hidden(rows[0],{'hidden_paths':[],'hidden_trees':[]})
    # Another node can have the same path without inheriting this rule.
    monkeypatch.setattr(node,'LOOK_MEDIA_LIBRARY',tmp_path/'other'/'media_library.json')
    assert not node._media_owner_hidden('/media/Junk/a.wav',node._media_owner_visibility())
    monkeypatch.setattr(node,'LOOK_MEDIA_LIBRARY',library)
    node._local_media_visibility({'path':'/media/Junk/a.wav','hidden':False})
    assert not node._local_media_catalog()['entries'][0]['fabric_hidden_by']
    with pytest.raises(ValueError):
        node._local_media_visibility({'path':'/outside','hidden':True})


def test_hide_batches_by_owner_and_updates_current_view(monkeypatch):
    lk=load_lk(); calls=[]
    rules={'paths':['/music/a.wav','/music/b.wav'],'trees':[]}
    class Response:
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def read(self): return json.dumps({'ok':True,'rules':rules}).encode()
    monkeypatch.setattr(lk.urllib.request,'urlopen',lambda request,**kwargs:calls.append(json.loads(request.data)) or Response())
    rows=[{'node':'m3','path':'/music/a.wav'},{'node':'m3','path':'/music/b.wav'}]
    assert lk._media_hide(rows)==2
    assert len(calls)==1 and len(calls[0]['paths'])==2
    assert all(lk._media_is_hidden(row) for row in rows)
    assert not lk._media_is_hidden({'node':'3090','path':'/music/a.wav'})


def test_ff_reuses_visible_catalog_for_typing_and_navigation(tmp_path,monkeypatch):
    import threading
    done=threading.Event(); done.set()
    paths=[tmp_path/f"song-{i}.mp3" for i in range(160000)]
    calls=[]
    original=renderer._catalog_matches
    monkeypatch.setattr(renderer,'_catalog_matches',lambda *args,**kwargs:calls.append(args[1]) or original(*args,**kwargs))
    monkeypatch.setattr(renderer,'_start_global_catalog',lambda root:(paths,done))
    monkeypatch.setattr(renderer.sys,'argv',['look.py',str(tmp_path),'--global-find'])
    def browse(*args,**kwargs):
        for query in ['song-10','song-100','song-100']:
            candidates=kwargs['candidates'](query)
            kwargs['rebuild'](query,candidates[0],80,set())
            kwargs['header_rows'](80)
        assert calls.count('')==2  # initial frame plus the cached visible set
        kwargs['on_hidden']()
        kwargs['candidates']('song-100')
        assert calls.count('')==3
    monkeypatch.setattr(renderer,'pager',browse)
    renderer.main()
