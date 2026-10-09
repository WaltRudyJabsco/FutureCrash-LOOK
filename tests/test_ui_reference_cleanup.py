import importlib.util
import io
import os
import threading
from importlib.machinery import SourceFileLoader
from pathlib import Path
from types import SimpleNamespace

from look import look_renderer as renderer
from tools import command_reference

ROOT=Path(__file__).resolve().parents[1]


def load_lk():
    spec=importlib.util.spec_from_loader('lk_palette_test',SourceFileLoader('lk_palette_test',str(ROOT/'look/lk')))
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def test_reference_surfaces_are_synchronized_and_cover_dispatch():
    for path,content in command_reference.outputs().items():
        assert path.read_text()==content
    version,forms,help_text,usage,options=command_reference.collect()
    names={row[0] for row in forms}
    assert {'lk doc','lk tldr','lk dash','lk fabric','lk ytd','lk mp','lh','lk hidden'}<=names
    text=(ROOT/'look/docs/REFERENCE.md').read_text()
    for detail in ['--kind','--limit','--selection','--detach','--holding','--relocate','S save playlist','C clear selection']:
        assert detail in text


def test_generator_detects_new_dispatch_and_printed_usage(tmp_path):
    (tmp_path/'look').mkdir()
    for name in ['lk','look_renderer.py','ytd.py','games.py']:
        (tmp_path/'look'/name).write_text((ROOT/'look'/name).read_text())
    script=tmp_path/'look/lk'
    script.write_text(script.read_text().replace('    if cmd=="doc":','    if cmd=="future-example":\n        print("usage: lk future-example --special VALUE")\n        return 0\n    if cmd=="doc":'))
    _,forms,_,usages,_=command_reference.collect(tmp_path)
    assert any(row[0]=='lk future-example' for row in forms)
    assert 'usage: lk future-example --special VALUE' in usages['look/lk']


def test_player_controls_fit_with_album_art_and_preserve_text(monkeypatch):
    lk=load_lk()
    monkeypatch.setattr(lk.sys.stdout,'isatty',lambda:True)
    monkeypatch.setattr(lk.shutil,'get_terminal_size',lambda fallback:os.terminal_size((72,24)))
    snap={'entry':{'artist':'Artist','title':'Song','album':'Album'},'state':'playing',
          'position':10,'duration':60,'index':0,'session':{'queue':[{}]}}
    monkeypatch.setattr(lk,'_media_status_snapshot',lambda:snap)
    monkeypatch.setattr(lk,'_media_cover_lines',lambda *args,**kwargs:['\x1b[32mART\x1b[0m']*11)
    monkeypatch.setattr(lk,'_media_remote_preview_state',lambda *args:('local',''))
    output=lk._media_player_render()
    lines=output.splitlines()
    assert all(len(lk._strip_ansi(line))==72-2 for line in lines)
    plain=lk._strip_ansi(output)
    for key in ['space play/pause','p/n previous/next','v visuals','q/Esc close player','PLAYING','ART']:
        assert key in plain
    assert '\x1b[' in output


def test_media_hints_are_plain_for_pipes_and_wrap_without_losing_actions(monkeypatch):
    lk=load_lk()
    monkeypatch.setattr(lk.sys.stdout,'isatty',lambda:False)
    result=lk._media_hints('Enter play · Q queue · S save playlist · C clear selection',32)
    assert '\x1b' not in result
    assert all(len(line)<=32 for line in result.splitlines())
    assert 'S save playlist' in result and 'C clear selection' in result


def test_ff_scan_does_not_drop_results_after_twenty_thousand(monkeypatch,tmp_path):
    monkeypatch.setattr(renderer.shutil,'which',lambda command:'/usr/bin/fd')
    paths=[str(tmp_path/f'file {index}') for index in range(20005)]+[str(tmp_path/' leading space')]
    proc=SimpleNamespace(stdout=io.StringIO('\n'.join(paths)+'\n'),wait=lambda timeout:0)
    monkeypatch.setattr(renderer.subprocess,'Popen',lambda *args,**kwargs:proc)
    catalog=[]; done=threading.Event()
    renderer._global_catalog_stream(tmp_path,catalog,done)
    assert done.is_set() and len(catalog)==20006
    assert catalog[-1].name==' leading space'


def test_ff_view_does_not_hide_later_selectable_matches(tmp_path):
    paths=[tmp_path/f'item {index}' for index in range(805)]
    view=renderer._catalog_view(paths,tmp_path,80,highlight_path=paths[-1])
    assert len(view)==807
    assert 'item 804' in renderer.strip_ansi(view[-1])


def test_ff_background_completion_refreshes_without_a_keystroke(tmp_path,monkeypatch):
    from unittest.mock import Mock
    class Terminal(io.StringIO):
        def isatty(self): return True
    monkeypatch.setattr(renderer.sys,'stdin',Mock(isatty=lambda:True,fileno=lambda:0))
    output=Terminal(); monkeypatch.setattr(renderer.sys,'stdout',output)
    monkeypatch.setattr(renderer.termios,'tcgetattr',lambda fd:[])
    monkeypatch.setattr(renderer.termios,'tcsetattr',lambda *args:None)
    monkeypatch.setattr(renderer.tty,'setcbreak',lambda fd:None)
    monkeypatch.setattr(renderer,'NativePreviewController',Mock)
    catalog=[]; done=False; calls=[]
    def key(**kwargs):
        nonlocal done
        calls.append(kwargs.get('timeout'))
        if len(calls)==1:
            catalog.append(tmp_path/'new result'); done=True
            return ''
        return 'Q'
    monkeypatch.setattr(renderer,'read_key',key)
    renderer.pager(['scanning'],24,80,force_interactive=True,
                   rebuild=lambda *args:[str(path) for path in catalog] or ['scanning'],
                   live_revision=lambda:(len(catalog),done))
    assert 'new result' in output.getvalue()
    assert calls==[.25,None]


def test_ff_only_stats_visible_rows_in_large_catalog(tmp_path,monkeypatch):
    paths=[tmp_path/f'item {index}' for index in range(25000)]
    calls=[]
    monkeypatch.setattr(Path,'is_dir',lambda path:calls.append(path) or False)
    view=renderer._catalog_view(paths,tmp_path,80)
    assert len(view)==25002 and not calls
    page=view[22000:22010]
    assert len(page)==10 and len(calls)<=20
